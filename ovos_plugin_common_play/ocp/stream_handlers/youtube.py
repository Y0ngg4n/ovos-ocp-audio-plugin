import enum


class YoutubeBackend(str, enum.Enum):
    YDL = "youtube-dl"
    PYTUBE = "pytube"
    PAFY = "pafy"


class YdlBackend(str, enum.Enum):
    YDL = "youtube-dl"
    YDLC = "youtube-dlc"
    YDLP = "yt-dlp"


class YoutubeLiveBackend(str, enum.Enum):
    PYTUBE = "pytube"
    YT_SEARCHER = "youtube_searcher"


def _parse_title(title):
    # try to extract_streams artist from title
    delims = ["-", ":", "|"]
    for d in delims:
        if d in title:
            removes = ["(Official Video)", "(Official Music Video)",
                       "(Lyrics)", "(Official)", "(Album Stream)",
                       "(Legendado)"]
            removes += [s.replace("(", "").replace(")", "") for s in removes] + \
                       [s.replace("[", "").replace("]", "") for s in removes]
            removes += [s.upper() for s in removes] + [s.lower() for s in
                                                       removes]
            removes += ["(HQ)", "()", "[]", "- HQ -"]
            for k in removes:
                title = title.replace(k, "")
            artist = title.split(d)[0]
            title = "".join(title.split(d)[1:])
            title = title.strip() or "..."
            artist = artist.strip() or "..."
            return title, artist
    return title, ""


def get_youtube_live_from_channel(url, backend=YoutubeLiveBackend.PYTUBE,
                                  fallback=True):
    if backend == YoutubeLiveBackend.PYTUBE:
        try:
            for vid in get_pytube_channel_livestreams(url):
                return vid
        except:
            if fallback:
                return get_youtube_live_from_channel(
                    url, backend=YoutubeLiveBackend.YT_SEARCHER, fallback=False)
            raise
    elif backend == YoutubeLiveBackend.YT_SEARCHER:
        try:
            for vid in get_youtubesearcher_channel_livestreams(url):
                return vid
        except:
            if fallback:
                return get_youtube_live_from_channel(
                    url, backend=YoutubeLiveBackend.PYTUBE,
                    fallback=False)
            raise
    else:
        if fallback:
            return get_youtube_live_from_channel(url,
                                                 backend=YoutubeLiveBackend.PYTUBE)
        raise ValueError("invalid backend")


def get_youtube_stream(url, backend=YoutubeBackend.PYTUBE,
                       fallback=True, audio_only=False,
                       ydl_backend=YdlBackend.YDL, best=True):
    try:
        if backend == YoutubeBackend.PYTUBE:
            return get_pytube_stream(url, best=best, audio_only=audio_only)
        if backend == YoutubeBackend.PAFY:
            return get_pafy_stream(url, audio_only=audio_only, best=best)
        return get_ydl_stream(url, fallback=fallback, backend=ydl_backend,
                              best=best, audio_only=audio_only)
    except:
        if fallback:
            if backend in [YoutubeBackend.PYTUBE, YoutubeBackend.PAFY]:
                return get_youtube_stream(url, backend=YoutubeBackend.YDL,
                                          audio_only=audio_only,
                                          fallback=False, best=best)
            return get_youtube_stream(url, backend=YoutubeBackend.PYTUBE,
                                      audio_only=audio_only,
                                      fallback=False, best=best)
        raise


def is_youtube(url):
    # TODO localization
    if not url:
        return False
    return "youtube.com/" in url or "youtu.be/" in url


def get_ydl_stream(url, preferred_ext=None, backend=YdlBackend.YDLP,
                   fallback=True, ydl_opts=None, audio_only=False, best=True):
    ydl_opts = ydl_opts or {
        "quiet": True,
        "hls_prefer_native": True,
        "verbose": False
    }

    if backend == YdlBackend.YDLP:
        try:
            import yt_dlp as youtube_dl
        except ImportError:
            if fallback:
                return get_ydl_stream(url, preferred_ext, YdlBackend.YDL,
                                      False)
            raise
    elif backend == YdlBackend.YDLC:
        try:
            import youtube_dlc as youtube_dl
        except ImportError:
            if fallback:
                return get_ydl_stream(url, preferred_ext, YdlBackend.YDL,
                                      False, audio_only=audio_only)
            raise
    elif backend == YdlBackend.YDL:
        import youtube_dl
    else:
        raise ValueError("invalid youtube-dl backend")

    kmaps = {"duration": "duration",
             "thumbnail": "image",
             "uploader": "artist",
             "title": "title",
             'webpage_url': "url"}
    info = {}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        meta = ydl.extract_info(url, download=False)
        for k, v in kmaps.items():
            if k in meta:
                info[v] = meta[k]

        if "entries" in meta:
            meta = meta["entries"][0]

        info["uri"] = _select_ydl_format(meta, audio_only=audio_only,
                                         best=best)
        title, artist = _parse_title(info["title"])
        info["title"] = title
        info["artist"] = artist or info.get("artist")
        info["is_live"] = meta.get("is_live", False)
    return info


def _select_ydl_format(meta, audio_only=False, preferred_ext=None, best=True):
    if not meta.get("formats"):
        # not all extractors return same format dict
        if meta.get("url"):
            return meta["url"]
        raise ValueError

    fmts = meta["formats"]
    if audio_only:
        # skip any stream that contains video
        fmts = [f for f in fmts if f.get('vcodec', "") == "none"]
    else:
        # skip video only streams (no audio / progressive streams only)
        fmts = [f for f in fmts if f.get('acodec', "") != "none"]

    if preferred_ext:
        fmts = [f for f in meta["formats"]
                if f.get('ext', "") == preferred_ext] or fmts

    # last is best (higher res)
    if best:
        return fmts[-1]["url"]
    return fmts[0]["url"]


def get_pafy_stream(url, audio_only=False, best=True):
    import pafy
    stream = pafy.new(url)
    meta = {
        "url": url,
        # "audio_stream": stream.getbestaudio().url,
        # "stream": stream.getbest().url,
        "author": stream.author,
        "image": stream.getbestthumb().split("?")[0],
        #        "description": stream.description,
        "length": stream.length * 1000,
        "category": stream.category,
        #        "upload_date": stream.published,
        #        "tags": stream.keywords
    }

    # TODO fastest vs best
    stream = None
    if audio_only:
        stream = stream.getbestaudio() or stream.getbest()
    else:
        stream = stream.getbest()
    if not stream:
        raise RuntimeError("Failed to extract stream")
    uri = stream.url
    meta["uri"] = uri
    title, artist = _parse_title(stream.title)
    meta["title"] = title
    meta["artist"] = artist or stream.author
    return meta


def get_pytube_stream(url, audio_only=False, best=True):
    from pytube import YouTube
    yt = YouTube(url)
    s = None
    if audio_only:
        s = yt.streams.filter(only_audio=True).order_by('abr')
    if not s:
        s = yt.streams.filter(progressive=True).order_by('resolution')

    if best:  # best quality
        s = s.last()
    else:  # fastest
        s = s.first()

    info = {
        "uri": s.url,
        "url": yt.watch_url,
        "title": yt.title,
        "author": yt.author,
        "image": yt.thumbnail_url,
        "length": yt.length * 1000
    }
    title, artist = _parse_title(info["title"])
    info["title"] = title
    info["artist"] = artist or info.get("author")
    return info


def get_pytube_channel_livestreams(url):
    from pytube import Channel
    yt = Channel(url)
    for v in yt.videos_generator():
        if v.vid_info.get('playabilityStatus', {}).get('liveStreamability'):
            title, artist = _parse_title(v.title)
            yield {
                "url": v.watch_url,
                "title": title,
                "artist": artist,
                "is_live": True,
                "image": v.thumbnail_url,
                "length": v.length * 1000
            }


def get_youtubesearcher_channel_livestreams(url):
    try:
        from youtube_searcher import extract_videos
        for e in extract_videos(url):
            if not e["is_live"]:
                continue
            title, artist = _parse_title(e["title"])
            yield {
                "url": "https://www.youtube.com/watch?v=" + e["videoId"],
                "is_live": True,
                "description": e["description"],
                "image": e["thumbnail"],
                "title": title,
                "artist": artist
            }
    except:
        pass


if __name__ == "__main__":
    lives = "https://www.youtube.com/channel/UCihCtNZnFkG62U4na9JsPJQ"
    for ch in get_youtubesearcher_channel_livestreams(lives):
        print(ch)
        break
    for ch in get_pytube_channel_livestreams(lives):
        print(ch)
        break

    exit()
   # print(get_youtube_live_from_channel(lives))
   # print(get_pytube_channel_livestreams(lives))

    # print(get_pytube_stream("https://www.youtube.com/watch?v=2Vw-8JuLT-8"))
    print(get_youtube_stream("https://www.youtube.com/watch?v=Ya3WXzEBL1E"))
    # print(get_pafy_stream(
    #    "https://www.youtube.com/watch?v=2Vw-8JuLT-8"))

    exit()
    """
        print(get_ydl_channel_livestream(
        "https://www.youtube.com/user/Euronews"))

    print(get_pytube_channel_livestream(
        "https://www.youtube.com/user/Euronews"))


    print(get_pytube_channel_livestream(
        "https://www.youtube.com/channel/UCQfwfsi5VrQ8yKZ-UWmAEFg"))
    print(get_pytube_channel_livestream(
        "https://www.youtube.com/channel/UCknLrEdhRCp1aegoMqRaCZg"))
    print(get_pytube_channel_livestream(
        "https://www.youtube.com/user/RussiaToday"))
"""
