"""
Compatibility wrapper for legacy imports.
"""

from backend.feature_extraction import extract_features


def featureExtraction(url):
    return extract_features(url)
