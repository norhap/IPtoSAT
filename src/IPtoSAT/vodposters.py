import hashlib
import json
import os
import tempfile
from urllib.parse import unquote, urlsplit


MARKED_CATEGORIES = "/etc/enigma2/iptosat_vod_categories.json"
POSTER_INDEX = "/etc/enigma2/iptosat_vod_posters.json"


def service_key(url):
	return hashlib.sha256(unquote(url).encode("utf-8")).hexdigest()


def provider_key(domain, port, username):
	identity = json.dumps([domain, port, username], ensure_ascii=False)
	return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def marked_categories(config):
	providers = read_json(MARKED_CATEGORIES, {})
	if not isinstance(providers, dict):
		raise ValueError("Invalid VOD categories")
	key = provider_key(config.domain.value, config.serverport.value, config.username.value)
	categories = providers.get(key, [])
	if not isinstance(categories, list) or not all(isinstance(item, str) for item in categories):
		raise ValueError("Invalid VOD categories")
	return key, providers, set(categories)


def read_json(path, default):
	try:
		with open(path, encoding="utf-8") as file:
			return json.load(file)
	except FileNotFoundError:
		return default


def save_json(path, data):
	directory = os.path.dirname(path)
	filename = None
	try:
		with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as file:
			filename = file.name
			json.dump(data, file, ensure_ascii=False)
		os.replace(filename, path)
	finally:
		if filename and os.path.exists(filename):
			os.unlink(filename)


def image_url(value):
	try:
		parsed = urlsplit(value)
		return value if parsed.scheme in ("http", "https") and parsed.hostname else ""
	except ValueError:
		return ""
