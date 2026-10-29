"""Category detection from file extension. Pure stdlib, original code."""
import os

CATEGORIES = {
    "Video": {"mp4", "mkv", "webm", "avi", "mov"},
    "Music": {"mp3", "wav", "flac", "ogg"},
    "Programs": {"exe", "msi", "apk"},
    "Documents": {"pdf", "docx", "xlsx", "txt"},
    "Archives": {"zip", "rar", "7z", "tar"},
    "Pictures": {"jpg", "jpeg", "png", "gif", "webp"},
}

def category_for(filename):
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    for name, exts in CATEGORIES.items():
        if ext in exts:
            return name
    return "Other"

def downloadable_extensions():
    out = set()
    for exts in CATEGORIES.values():
        out.update(exts)
    out.update({"iso", "dmg", "gz", "bz2", "xz", "epub", "csv"})
    return out
