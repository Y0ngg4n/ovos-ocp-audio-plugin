import tempfile
from os.path import basename

try:
    import audio_metadata
except ImportError:  # common conflicts with attrs version.... replace ASAP
    audio_metadata = None
from ovos_plugin_common_play.ocp.status import TrackState, PlaybackType


def extract_metadata(uri):
    meta = {"uri": uri,
            "title": basename(uri),
            "playback": PlaybackType.AUDIO,
            "status": TrackState.DISAMBIGUATION}
    if not audio_metadata:
        return meta
    m = audio_metadata.load(uri.replace("file://", ""))
    if m.tags:
        if m.tags.get("title"):
            meta["title"] = m.tags.title[0]
        if m.tags.get("album"):
            meta["album"] = m.tags.album[0]

        if m.tags.get("artist"):
            meta["artist"] = m.tags.artist[0]
        elif m.tags.get("composer"):
            meta["artist"] = m.tags.composer[0]

        if m.tags.get("date"):
            meta["date"] = m.tags.date[0]
        if m.tags.get("audiolength"):
            meta["duration"] = m.tags.audiolength[0]
        if m.tags.get("genre"):
            meta["genre"] = m.tags.genre[0]

    if m.pictures:
        try:
            img_path = f"{tempfile.gettempdir()}/{meta['title']}.jpg"
            with open(img_path, "wb") as f:
                f.write(m.pictures[0].data)
            meta["image"]: img_path
        except:
            pass
    return meta
