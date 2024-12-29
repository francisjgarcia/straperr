from common import post_event

# Test data simulating the "ManualInteractionRequired" event for the series
# "Squid Game"
test_data = {
    "series": {
        "id": 337,
        "title": "Squid Game",
        "titleSlug": "squid-game",
        "path": "/data/FullHD/Squid Game (2021)",
        "tvdbId": 383275,
        "tvMazeId": 43687,
        "tmdbId": 93405,
        "imdbId": "tt10919420",
        "type": "standard",
        "year": 2021,
        "genres": ["Action", "Drama", "Mystery", "Thriller"],
        "images": [
            {
                "coverType": "banner",
                "url": (
                    "/MediaCover/337/banner.jpg?"
                    "lastWrite=638696792958472753"
                ),
                "remoteUrl": (
                    "https://artworks.thetvdb.com/banners/v4/series/383275/"
                    "banners/614429e09acf6.jpg"
                ),
            },
            {
                "coverType": "poster",
                "url": (
                    "/MediaCover/337/poster.jpg?"
                    "lastWrite=638696792958712753"
                ),
                "remoteUrl": (
                    "https://artworks.thetvdb.com/banners/v4/series/383275/"
                    "posters/6151351c5420c.jpg"
                ),
            },
            {
                "coverType": "fanart",
                "url": (
                    "/MediaCover/337/fanart.jpg?"
                    "lastWrite=638696792958792753"
                ),
                "remoteUrl": (
                    "https://artworks.thetvdb.com/banners/v4/series/383275/"
                    "backgrounds/61131e54d37c6.jpg"
                ),
            },
            {
                "coverType": "clearlogo",
                "url": (
                    "/MediaCover/337/clearlogo.png?"
                    "lastWrite=638696792958792753"
                ),
                "remoteUrl": (
                    "https://artworks.thetvdb.com/banners/v4/series/383275/"
                    "clearlogo/6146437006bcb.png"
                ),
            },
        ],
        "tags": ["fullhd"],
    },
    "episodes": [
        {
            "id": 22995,
            "episodeNumber": 1,
            "seasonNumber": 2,
            "title": "Bread and Lottery",
            "airDate": "2024-12-26",
            "airDateUtc": "2024-12-26T22:00:00Z",
            "seriesId": 337,
            "tvdbId": 10617348,
        },
        {
            "id": 29776,
            "episodeNumber": 2,
            "seasonNumber": 2,
            "title": "TBA",
            "airDate": "2024-12-26",
            "airDateUtc": "2024-12-26T22:00:00Z",
            "seriesId": 337,
            "tvdbId": 10774412,
        },
        {
            "id": 29777,
            "episodeNumber": 3,
            "seasonNumber": 2,
            "title": "TBA",
            "airDate": "2024-12-26",
            "airDateUtc": "2024-12-26T22:00:00Z",
            "seriesId": 337,
            "tvdbId": 10774413,
        },
        {
            "id": 29778,
            "episodeNumber": 4,
            "seasonNumber": 2,
            "title": "TBA",
            "airDate": "2024-12-26",
            "airDateUtc": "2024-12-26T22:00:00Z",
            "seriesId": 337,
            "tvdbId": 10774414,
        },
        {
            "id": 29779,
            "episodeNumber": 5,
            "seasonNumber": 2,
            "title": "TBA",
            "airDate": "2024-12-26",
            "airDateUtc": "2024-12-26T22:00:00Z",
            "seriesId": 337,
            "tvdbId": 10774415,
        },
        {
            "id": 29780,
            "episodeNumber": 6,
            "seasonNumber": 2,
            "title": "TBA",
            "airDate": "2024-12-26",
            "airDateUtc": "2024-12-26T22:00:00Z",
            "seriesId": 337,
            "tvdbId": 10774416,
        },
        {
            "id": 30062,
            "episodeNumber": 7,
            "seasonNumber": 2,
            "title": "TBA",
            "airDate": "2024-12-26",
            "airDateUtc": "2024-12-26T22:00:00Z",
            "seriesId": 337,
            "tvdbId": 10863921,
        },
    ],
    "downloadInfo": {
        "quality": "WEBDL-1080p",
        "qualityVersion": 1,
        "title": (
            "El juego del calamar (2021) S02 [PACK][NF WEB-DL 1080p AVC ES "
            "DD+ 5.1][HDO]"
        ),
        "size": 22023267376,
    },
    "downloadClient": "Transmission",
    "downloadClientType": "Transmission",
    "downloadId": (
        "4F2440FB4008ADAE1A1B855CE3F4BA4E5D952BDC"
    ),
    "downloadStatus": "Warning",
    "downloadStatusMessages": [
        {
            "title": (
                "El juego del calamar (2021) S02 [PACK][NF WEB-DL 1080p "
                "AVC ES DD+ 5.1][HDO]"
            ),
            "messages": [
                (
                    "Found matching series via grab history, but release was "
                    "matched to series by ID. Automatic import is not "
                    "possible. See the FAQ for details."
                )
            ],
        }
    ],
    "customFormatInfo": {
        "customFormats": [],
        "customFormatScore": 0,
    },
    "release": {
        "releaseTitle": (
            "El juego del calamar (2021) S02 [PACK][NF WEB-DL 1080p AVC ES "
            "DD+ 5.1][HDO] SPANiSH"
        ),
        "indexer": "HD-Olimpo (API) (Prowlarr)",
        "size": 22023268352,
        "releaseType": "seasonPack",
    },
    "eventType": "ManualInteractionRequired",
    "instanceName": "TestInstance",
    "applicationUrl": (
        "https://sonarr.francisjgarcia.es"
    ),
}

# Call post_event to simulate manual interaction required for this event
if __name__ == "__main__":
    post_event(test_data)
