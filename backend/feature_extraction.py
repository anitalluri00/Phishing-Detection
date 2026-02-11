from __future__ import annotations

import ipaddress
import os
import re
import socket
from datetime import datetime
from urllib.parse import quote, urljoin, urlparse

import requests
import urllib.request
import whois
from bs4 import BeautifulSoup


SHORTENER_PATTERN = re.compile(
    r"bit\.ly|goo\.gl|shorte\.st|go2l\.ink|x\.co|ow\.ly|t\.co|tinyurl|tr\.im|is\.gd|cli\.gs|"
    r"yfrog\.com|migre\.me|ff\.im|tiny\.cc|url4\.eu|twit\.ac|su\.pr|twurl\.nl|snipurl\.com|"
    r"short\.to|BudURL\.com|ping\.fm|post\.ly|Just\.as|bkite\.com|snipr\.com|fic\.kr|loopt\.us|"
    r"doiop\.com|short\.ie|kl\.am|wp\.me|rubyurl\.com|om\.ly|to\.ly|bit\.do|t\.co|lnkd\.in|"
    r"db\.tt|qr\.ae|adf\.ly|goo\.gl|bitly\.com|cur\.lv|tinyurl\.com|ow\.ly|bit\.ly|ity\.im|"
    r"q\.gs|is\.gd|po\.st|bc\.vc|twitthis\.com|u\.to|j\.mp|buzurl\.com|cutt\.us|u\.bb|yourls\.org|"
    r"x\.co|prettylinkpro\.com|scrnch\.me|filoops\.info|vzturl\.com|qr\.net|1url\.com|tweez\.me|v\.gd|tr\.im|link\.zip\.net"
)


def _safe_request(url: str):
    def host_is_blocked(hostname: str | None) -> bool:
        if not hostname:
            return True

        host = hostname.lower()
        if host == "localhost" or host.endswith(".local"):
            return True

        try:
            ip = ipaddress.ip_address(host)
            return (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            )
        except ValueError:
            pass

        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            # Keep behavior resilient in restricted DNS environments.
            return False

        for info in infos:
            try:
                ip = ipaddress.ip_address(info[4][0])
            except ValueError:
                continue
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                return True
        return False

    redirects = 0
    current_url = url

    try:
        for _ in range(5):
            parsed = urlparse(current_url)
            if parsed.scheme not in {"http", "https"}:
                return None, redirects
            if host_is_blocked(parsed.hostname):
                return None, redirects

            response = requests.get(
                current_url,
                timeout=5,
                headers={"User-Agent": "Mozilla/5.0 (compatible; PhishDetect/1.0)"},
                allow_redirects=False,
            )

            if response.is_redirect and response.headers.get("Location"):
                redirects += 1
                current_url = urljoin(current_url, response.headers["Location"])
                continue

            return response, redirects
    except requests.RequestException:
        return None, redirects

    return None, redirects


def _having_ip(url: str) -> int:
    try:
        ipaddress.ip_address(urlparse(url).hostname or "")
        return 1
    except Exception:
        return 0


def _have_at_sign(url: str) -> int:
    return 1 if "@" in url else 0


def _url_length(url: str) -> int:
    return 1 if len(url) >= 54 else 0


def _url_depth(url: str) -> int:
    return len([part for part in urlparse(url).path.split("/") if part])


def _redirection(url: str) -> int:
    pos = url.rfind("//")
    return 1 if pos > 7 else 0


def _http_domain(url: str) -> int:
    return 1 if "https" not in (urlparse(url).scheme or "") else 0


def _tiny_url(url: str) -> int:
    return 1 if SHORTENER_PATTERN.search(url) else 0


def _prefix_suffix(url: str) -> int:
    return 1 if "-" in urlparse(url).netloc else 0


def _web_traffic(url: str) -> int:
    # Alexa endpoint is effectively deprecated/unreliable.
    # Keep lookup optional; default to neutral value to avoid systematic false positives.
    if os.getenv("ENABLE_WEB_TRAFFIC_LOOKUP", "false").lower() != "true":
        return 0

    try:
        q = quote(url, safe="")
        rank = (
            BeautifulSoup(
                urllib.request.urlopen(
                    "http://data.alexa.com/data?cli=10&dat=s&url=" + q, timeout=5
                ).read(),
                "xml",
            )
            .find("REACH")
            .get("RANK")
        )
        return 1 if int(rank) < 100000 else 0
    except Exception:
        return 0


def _domain_age(domain_info) -> int:
    try:
        creation_date = domain_info.creation_date
        expiration_date = domain_info.expiration_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0]
        if isinstance(creation_date, str):
            creation_date = datetime.strptime(creation_date, "%Y-%m-%d")
        if isinstance(expiration_date, str):
            expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d")
        if not creation_date or not expiration_date:
            return 1
        months = abs((expiration_date - creation_date).days) / 30
        return 1 if months < 6 else 0
    except Exception:
        return 1


def _domain_end(domain_info) -> int:
    try:
        expiration_date = domain_info.expiration_date
        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0]
        if isinstance(expiration_date, str):
            expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d")
        if not expiration_date:
            return 1
        months = abs((expiration_date - datetime.now()).days) / 30
        return 1 if months >= 6 else 0
    except Exception:
        return 1


def _iframe(response) -> int:
    if response is None:
        return 1
    return 0 if re.findall(r"<iframe|<frameBorder>", response.text, re.IGNORECASE) else 1


def _mouse_over(response) -> int:
    if response is None:
        return 1
    return 1 if re.findall(r"<script>.+onmouseover.+</script>", response.text) else 0


def _right_click(response) -> int:
    if response is None:
        return 1
    return 1 if re.findall(r"event.button ?== ?2", response.text) else 0


def _forwarding(redirect_count: int | None) -> int:
    if redirect_count is None:
        return 1
    return 1 if redirect_count > 2 else 0


def extract_features(url: str) -> list[float]:
    """
    Returns model features in this exact order:
    Have_IP, Have_At, URL_Length, URL_Depth, Redirection,
    https_Domain, TinyURL, Prefix/Suffix, DNS_Record, Web_Traffic,
    Domain_Age, Domain_End, iFrame, Mouse_Over, Right_Click, Web_Forwards
    """
    response, redirect_count = _safe_request(url)

    dns = 0
    domain_info = None
    try:
        domain_info = whois.whois(urlparse(url).netloc)
    except Exception:
        dns = 1

    forwarding_score = _forwarding(redirect_count if response is not None else None)

    return [
        _having_ip(url),
        _have_at_sign(url),
        _url_length(url),
        _url_depth(url),
        _redirection(url),
        _http_domain(url),
        _tiny_url(url),
        _prefix_suffix(url),
        dns,
        _web_traffic(url),
        1 if dns == 1 else _domain_age(domain_info),
        1 if dns == 1 else _domain_end(domain_info),
        _iframe(response),
        _mouse_over(response),
        _right_click(response),
        forwarding_score,
    ]
