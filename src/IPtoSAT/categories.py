import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .vodposters import provider_key, read_json, save_json


SELECTION_FILE = "/etc/enigma2/iptosatyourcatall.selection.json"
TYPES = ("live", "vod", "series")


def current_provider(config):
	return provider_key(config.domain.value, config.serverport.value, config.username.value)


def read_selections():
	data = read_json(SELECTION_FILE, {})
	if not isinstance(data, dict):
		raise ValueError("Invalid category selections")
	for provider, entry in data.items():
		if not isinstance(provider, str) or not isinstance(entry, dict):
			raise ValueError("Invalid category selections")
		catalog = entry.get("catalog")
		excluded = entry.get("excluded")
		if not isinstance(catalog, dict) or set(catalog) != set(TYPES) or not isinstance(excluded, list):
			raise ValueError("Invalid category selections")
		if not all(isinstance(name, str) for name in excluded):
			raise ValueError("Invalid excluded categories")
		for names in catalog.values():
			if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
				raise ValueError("Invalid category catalog")
	return data


def fetch_catalog(domain, port, username, password):
	host = domain.rstrip("/") + ":" + port
	catalog = {}
	for kind in TYPES:
		query = urlencode({"username": username, "password": password, "action": "get_%s_categories" % kind})
		request = Request(host + "/player_api.php?" + query, headers={"User-Agent": "Mozilla/5.0"})
		with urlopen(request, timeout=15) as response:
			data = json.load(response)
		if not isinstance(data, list):
			raise ValueError("Invalid category response")
		names = []
		seen = set()
		for item in data:
			if not isinstance(item, dict) or not isinstance(item.get("category_name"), str):
				raise ValueError("Invalid category response")
			name = item["category_name"]
			if not name or any(ord(char) < 32 for char in name):
				raise ValueError("Invalid category name")
			if name not in seen:
				names.append(name)
				seen.add(name)
		catalog[kind] = names
	return catalog


def category_name(name):
	for old, new in ((":", ""), (".", ""), ("|", ""), ("   ", " "), ("  ", " "), ("ñ", ""), ("Ç", ""), ("Â", ""), ("Ú", ""), ("Í", ""), ("É", ""), ("Ó", ""), ("⭐", ""), ("/", ""), ("•", ""), ("⚡", ""), ("⚽", ""), ("Ñ", "N"), ("Ë", "E")):
		name = name.replace(old, new)
	return name.replace("FOR ADULT", "For Adult")


def entries(entry, kind):
	kinds = TYPES if kind == "all" else (kind,)
	if any(value not in TYPES for value in kinds):
		raise ValueError("Invalid category type")
	return [(category_type, name) for category_type in kinds for name in entry["catalog"][category_type]]


def category_map(entry, kind):
	excluded = set(entry["excluded"])
	result = {}
	for _, name in entries(entry, kind):
		if name not in excluded:
			key = category_name(name)
			if not key:
				raise ValueError("Invalid bouquet name")
			result.setdefault(key, [])
			if name not in result[key]:
				result[key].append(name)
	return result


def category_matchers(entry, kind):
	excluded = set(entry["excluded"])
	selected = {name for _, name in entries(entry, kind)}
	names = {name for _, name in entries(entry, "all")}
	result = {}
	for name in names:
		bouquet = None if name in excluded or name not in selected else category_name(name)
		groups = {name.replace("|  ", "| ")}
		if "[" in name and "]" in name:
			groups.add(name.replace("[", "").replace("]", "|").replace("|  ", "| "))
		for group in groups:
			if group in result and result[group] != bouquet:
				raise ValueError("Categories with the same playlist group cannot have different selections")
			result[group] = bouquet
	return sorted(result.items(), key=lambda item: len(item[0]), reverse=True)


def match_category(matchers, group):
	for name, bouquet in matchers:
		if group.startswith(name):
			return bouquet
	return None


def excluded_bouquets(entry, kind):
	included = set(category_map(entry, kind))
	return {category_name(name) for _, name in entries(entry, kind) if name in entry["excluded"]} - included


def save_provider(provider, catalog, excluded):
	data = read_selections()
	entry = {"catalog": catalog, "excluded": sorted(set(excluded))}
	category_map(entry, "all")
	category_matchers(entry, "all")
	data[provider] = entry
	save_json(SELECTION_FILE, data)


def remove_excluded_entries(bouquets_path, favorite_name, names):
	if not names or not os.path.exists(bouquets_path):
		return
	filenames = {"userbouquet.%s_%s.tv" % (favorite_name, name) for name in names}
	with open(bouquets_path, encoding="utf-8") as file:
		lines = file.readlines()
	remaining = [line for line in lines if not any('FROM BOUQUET "%s"' % name in line for name in filenames)]
	if remaining == lines:
		return
	import tempfile
	filename = None
	try:
		with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=os.path.dirname(bouquets_path), delete=False) as file:
			filename = file.name
			file.writelines(remaining)
		os.replace(filename, bouquets_path)
	finally:
		if filename and os.path.exists(filename):
			os.unlink(filename)
