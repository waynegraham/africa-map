"""Download OSM museums, libraries and archives as GeoJSON points."""
import json
import math
from pathlib import Path
import re
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_ENDPOINT = 'https://overpass-api.de/api/interpreter'


def build_query(alpha_2, timeout=180):
    """Select ISO-tagged administrative areas, including territories."""
    if not re.fullmatch(r'[A-Z]{2}', alpha_2):
        raise ValueError(f'Invalid ISO alpha-2 code: {alpha_2!r}')
    return f'''[out:json][timeout:{timeout}];
area["ISO3166-1"="{alpha_2}"]["boundary"="administrative"]->.country;
.country out ids;
(
  nwr["tourism"="museum"](area.country);
  nwr["amenity"="library"](area.country);
  nwr["amenity"="archive"](area.country);
  nwr["office"="archive"](area.country);
  nwr["government"="archive"](area.country);
);
out center tags;'''


def _request_json(query, endpoint, timeout, attempts, *, retry_delay=30, max_retry_delay=300):
    request = Request(endpoint, data=urlencode({'data': query}).encode(),
                      headers={'User-Agent': 'africa-map-poi-downloader/1.0',
                               'Content-Type': 'application/x-www-form-urlencoded'})
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout + 60) as response:
                payload = json.load(response)
            if payload.get('remark'):
                raise RuntimeError(payload['remark'])
            if not isinstance(payload.get('elements'), list):
                raise ValueError('Overpass response has no elements list')
            return payload
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError) as error:
            if isinstance(error, HTTPError) and error.code not in (429, 500, 502, 503, 504):
                raise
            if attempt + 1 == attempts:
                raise
            delay = min(max_retry_delay, retry_delay * 2 ** attempt)
            delay += random.uniform(0, min(5, delay * 0.1))
            if isinstance(error, HTTPError):
                retry_after = error.headers.get('Retry-After', '')
                if retry_after.isdigit():
                    delay = max(delay, int(retry_after))
                elif retry_after:
                    try:
                        until = parsedate_to_datetime(retry_after)
                        delay = max(delay, (until - datetime.now(timezone.utc)).total_seconds())
                    except (TypeError, ValueError, OverflowError):
                        pass
            print(f'  Request attempt {attempt + 1}/{attempts} failed: {error}. '
                  f'Retrying in {delay:.1f}s...', flush=True)
            time.sleep(delay)


def elements_to_features(elements, country):
    """Keep node coordinates and bounding-box centers of ways/relations."""
    features = {}
    for element in elements:
        kind = element.get('type')
        if kind not in ('node', 'way', 'relation'):
            continue
        location = element if kind == 'node' else element.get('center', {})
        lat, lon = location.get('lat'), location.get('lon')
        if (not isinstance(lat, (int, float)) or not isinstance(lon, (int, float))
                or not math.isfinite(lat) or not math.isfinite(lon)
                or not -90 <= lat <= 90 or not -180 <= lon <= 180):
            raise ValueError(f'Missing or invalid coordinates for {kind}/{element.get("id")}')
        identity = f'{kind}/{element["id"]}'
        tags = element.get('tags', {})
        categories = []
        if tags.get('tourism') == 'museum':
            categories.append('museum')
        if tags.get('amenity') == 'library':
            categories.append('library')
        if any(tags.get(key) == 'archive' for key in ('amenity', 'office', 'government')):
            categories.append('archive')
        features[identity] = {
            'type': 'Feature', 'id': identity,
            'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
            'properties': {'osm_type': kind, 'osm_id': element['id'],
                           'country': country['country'], 'alpha_2': country['alpha_2'],
                           'countries': [country['alpha_2']], 'categories': categories,
                           'name': tags.get('name'), 'tags': tags},
        }
    return list(features.values())


def _write_json(path, value):
    # Replace only after the complete document has been serialized.
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def download_africa_pois(countries_path='iso_3166_1_africa.json', output_dir='data/pois',
                         *, country_codes=None, endpoint=DEFAULT_ENDPOINT,
                         timeout=180, attempts=5, pause_seconds=5,
                         retry_delay=30, max_retry_delay=300, resume=False):
    """Save country files, africa_pois.geojson and download_report.json.

    country_codes optionally limits the run, e.g. ['LS']. Failed countries
    are recorded and omitted from the combined file; inspect the report
    before treating that file as complete. With resume=True, valid existing
    country files are reused and missing countries are requested again.
    Otherwise each run refreshes selected countries. attempts includes the
    initial request. Retries use exponential backoff with jitter and honor
    Retry-After; timeout is the server query limit, with 60s extra for HTTP.
    No third-party dependencies are required.
    """
    if (not isinstance(timeout, int) or not isinstance(attempts, int)
            or timeout < 1 or attempts < 1 or pause_seconds < 0
            or not math.isfinite(pause_seconds) or retry_delay < 0
            or not math.isfinite(retry_delay) or max_retry_delay < retry_delay
            or not math.isfinite(max_retry_delay)):
        raise ValueError('Use positive integer timeout/attempts, nonnegative finite delays, '
                         'and max_retry_delay >= retry_delay')
    countries = json.loads(Path(countries_path).read_text(encoding='utf-8'))
    if country_codes is not None:
        selected = {code.upper() for code in country_codes}
        unknown = selected - {country['alpha_2'] for country in countries}
        if unknown:
            raise ValueError(f'Unknown country codes: {sorted(unknown)}')
        countries = [country for country in countries if country['alpha_2'] in selected]
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = {'successful': [], 'failed': [], 'source': 'OpenStreetMap contributors',
              'endpoint': endpoint}
    combined = {}
    for index, country in enumerate(countries):
        code = country['alpha_2']
        print(f'{index + 1}/{len(countries)}: {country["country"]} ({code})', flush=True)
        cached = None
        if resume and (output / f'{code}.geojson').exists():
            try:
                cached = json.loads((output / f'{code}.geojson').read_text(encoding='utf-8'))
                if cached.get('type') != 'FeatureCollection' or not isinstance(cached.get('features'), list):
                    raise ValueError('Invalid cached GeoJSON')
                for feature in cached['features']:
                    if (feature.get('type') != 'Feature' or not feature.get('id')
                            or feature.get('properties', {}).get('alpha_2') != code
                            or feature.get('geometry', {}).get('type') != 'Point'):
                        raise ValueError('Invalid cached POI')
            except (OSError, ValueError, AttributeError, TypeError):
                cached = None
        try:
            if cached is not None:
                features = cached['features']
                print(f'  Reusing {len(features)} cached POIs', flush=True)
            else:
                payload = _request_json(build_query(code, timeout), endpoint, timeout, attempts,
                                        retry_delay=retry_delay, max_retry_delay=max_retry_delay)
                if not any(element.get('type') == 'area' for element in payload['elements']):
                    raise ValueError('No ISO-tagged administrative area found; boundary requires manual review')
                features = elements_to_features(payload['elements'], country)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError) as error:
            report['failed'].append({'alpha_2': code, 'country': country['country'], 'error': str(error)})
            print(f'  Failed: {error}', flush=True)
        else:
            _write_json(output / f'{code}.geojson', {'type': 'FeatureCollection', 'features': features})
            report['successful'].append({'alpha_2': code, 'count': len(features)})
            for feature in features:
                # Country files may have inherited memberships from an older combined run.
                feature['properties']['countries'] = [code]
                if feature['id'] in combined:
                    combined[feature['id']]['properties']['countries'].append(code)
                else:
                    combined[feature['id']] = feature
            print(f'  Saved {len(features)} POIs', flush=True)
        # Persist progress so an interrupted notebook can be resumed.
        report['complete'] = index + 1 == len(countries) and not report['failed']
        report['feature_count'] = len(combined)
        _write_json(output / 'download_report.json', report)
        if cached is None and index + 1 < len(countries):
            time.sleep(pause_seconds)
    report['complete'] = not report['failed']
    report['feature_count'] = len(combined)
    _write_json(output / 'africa_pois.geojson', {'type': 'FeatureCollection', 'features': list(combined.values())})
    _write_json(output / 'download_report.json', report)
    return report
