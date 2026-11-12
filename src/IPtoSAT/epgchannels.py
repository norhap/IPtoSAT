import re
import stat
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from os import chmod, replace, stat as os_stat, unlink
from os.path import abspath, basename, dirname, exists
from urllib.request import Request, urlopen
from shutil import copy2


EPG_SOURCE_IDS_URL = "https://epgshare01.online/epgshare01/epg_ripper_ES1.txt"
CHANNEL_LINE_RE = re.compile(r'(?m)^([ \t]*<channel\b[^>]*\bid=")([^"]+)(")')
EPG_SECTION_RE = re.compile(r"^--\s*epg_ripper_ES1\s*--$", re.IGNORECASE)
NEXT_SECTION_RE = re.compile(r"^--\s*epg_ripper_", re.IGNORECASE)
GENERIC_ID_TOKENS = {"canal", "channel", "hd", "por", "tv", "uhd"}
PREFIX_ID_TOKENS = {"amc", "c"}


def _channelIdKeys(channel_id):
	name = unicodedata.normalize("NFKD", channel_id)
	name = name.encode("ascii", "ignore").decode("ascii").lower()
	tokens = re.findall(r"[a-z0-9]+\+?", name)
	if tokens and tokens[-1] == "es":
		tokens.pop()
	if not tokens:
		return set()

	keys = set()

	def add_variants(index, selected):
		if index == len(tokens):
			if selected:
				keys.add(tuple(sorted(selected)))
			return
		token = tokens[index]
		add_variants(index + 1, selected + [token])
		if token in GENERIC_ID_TOKENS or token.isdigit() or (index == 0 and token in PREFIX_ID_TOKENS):
			add_variants(index + 1, selected)

	add_variants(0, [])
	return keys


def parseES1ChannelIds(contents):
	text = contents.decode("utf-8-sig") if isinstance(contents, bytes) else contents
	channel_ids = set()
	in_section = False
	for line in text.splitlines():
		line = line.strip()
		if not in_section:
			if EPG_SECTION_RE.match(line):
				in_section = True
			continue
		if NEXT_SECTION_RE.match(line):
			break
		if not line or re.match(r"^\d{12}$", line) or line.startswith("# "):
			continue
		channel_ids.add(line)
	if not in_section or not channel_ids:
		raise ValueError("The ES1 channel-ID list is missing or empty")
	return channel_ids


def reconcileChannelIds(channels_xml, source_ids):
	root = ET.fromstring(channels_xml)
	mapped_channels = root.findall("channel")
	mapped_ids = {channel.get("id", "").lower() for channel in mapped_channels}
	available_ids = {channel_id.lower() for channel_id in source_ids}
	id_keys = {channel_id: _channelIdKeys(channel_id) for channel_id in source_ids}
	replacements = {}
	unmatched = []
	ambiguous = {}

	for channel in mapped_channels:
		old_id = channel.get("id", "")
		old_id_lower = old_id.lower()
		if not old_id_lower.endswith(".es") or old_id_lower in available_ids:
			continue
		old_keys = _channelIdKeys(old_id)
		candidates = {
			channel_id
			for channel_id, keys in id_keys.items()
			if channel_id.lower() not in mapped_ids and old_keys.intersection(keys)
		}
		if len(candidates) == 1:
			new_id = candidates.pop()
			replacements[old_id] = new_id
		elif candidates:
			ambiguous[old_id] = sorted(candidates)
		else:
			unmatched.append(old_id)

	target_counts = {}
	for new_id in replacements.values():
		target_counts[new_id] = target_counts.get(new_id, 0) + 1
	duplicate_targets = {
		new_id for new_id, count in target_counts.items()
		if count > 1
	}
	for old_id, new_id in list(replacements.items()):
		if new_id in duplicate_targets:
			del replacements[old_id]
			ambiguous[old_id] = [new_id]

	if not replacements:
		return channels_xml, {
			"updated": [],
			"unmatched": unmatched,
			"ambiguous": ambiguous,
		}

	def replace_id(match):
		old_id = match.group(2)
		return match.group(1) + replacements.get(old_id, old_id) + match.group(3)

	updated_xml = CHANNEL_LINE_RE.sub(replace_id, channels_xml)
	updated_root = ET.fromstring(updated_xml)
	if len(updated_root.findall("channel")) != len(mapped_channels):
		raise ValueError("Updating channel IDs changed the XML mapping structure")
	return updated_xml, {
		"updated": list(replacements.items()),
		"unmatched": unmatched,
		"ambiguous": ambiguous,
	}


def updateEPGChannelIds(channels_path):
	if not exists(channels_path):
		raise FileNotFoundError("EPGImport channel map not found: " + channels_path)

	request = Request(EPG_SOURCE_IDS_URL, headers={"User-Agent": "IPToSAT EPG ID updater"})
	with urlopen(request, timeout=15) as response:
		source_ids = parseES1ChannelIds(response.read())

	with open(channels_path, "r", encoding="utf-8", newline="") as channel_file:
		channels_xml = channel_file.read()
	updated_xml, report = reconcileChannelIds(channels_xml, source_ids)
	if not report["updated"]:
		return report

	path = abspath(channels_path)
	backup_path = path + ".bak"
	if not exists(backup_path):
		copy2(path, backup_path)

	file_mode = stat.S_IMODE(os_stat(path).st_mode)
	temp_path = None
	try:
		with tempfile.NamedTemporaryFile(
			mode="w",
			encoding="utf-8",
			newline="",
			dir=dirname(path),
			prefix=basename(path) + ".",
			suffix=".tmp",
			delete=False,
		) as temp_file:
			temp_path = temp_file.name
			temp_file.write(updated_xml)
			temp_file.flush()
		chmod(temp_path, file_mode)
		replace(temp_path, path)
	except Exception:
		if temp_path and exists(temp_path):
			unlink(temp_path)
		raise

	return report
