# API Index

## CLI

List available methods:

```powershell
python skills/xhs-apis/scripts/xhs_api_tool.py list
```

Call a method with inline JSON:

```powershell
python skills/xhs-apis/scripts/xhs_api_tool.py call <namespace> <method> --params "{...}"
```

Call a method with a JSON file:

```powershell
python skills/xhs-apis/scripts/xhs_api_tool.py call <namespace> <method> --params-file .\payload.json
```

Write the result to a file:

```powershell
python skills/xhs-apis/scripts/xhs_api_tool.py call pc get_user_self_info --params "{...}" --out .\result.json
```

## Namespace Notes

- `pc`: calls the methods from `xhs_pc_apis.py`.
- `creator`: calls the methods from `xhs_creator_apis.py`.
- For `creator`, the CLI accepts `cookies_str` and converts it to the `cookies` dict expected by most source methods.
- For `creator.upload_media`, `creator.get_file_info`, and `creator.post_note`, file paths are read into bytes automatically by the CLI.

## PC APIs

- `get_homefeed_all_channel(cookies_str: str, proxies: dict = None)`
- `get_homefeed_recommend(category, cursor_score, refresh_type, note_index, cookies_str: str, proxies: dict = None)`
- `get_homefeed_recommend_by_num(category, require_num, cookies_str: str, proxies: dict = None)`
- `get_user_info(user_id: str, cookies_str: str, proxies: dict = None)`
- `get_user_self_info(cookies_str: str, proxies: dict = None)`
- `get_user_self_info2(cookies_str: str, proxies: dict = None)`
- `get_user_note_info(user_id: str, cursor: str, cookies_str: str, xsec_token='', xsec_source='', proxies: dict = None)`
- `get_user_all_notes(user_url: str, cookies_str: str, proxies: dict = None)`
- `get_user_like_note_info(user_id: str, cursor: str, cookies_str: str, xsec_token='', xsec_source='', proxies: dict = None)`
- `get_user_all_like_note_info(user_url: str, cookies_str: str, proxies: dict = None)`
- `get_user_collect_note_info(user_id: str, cursor: str, cookies_str: str, xsec_token='', xsec_source='', proxies: dict = None)`
- `get_user_all_collect_note_info(user_url: str, cookies_str: str, proxies: dict = None)`
- `get_note_info(url: str, cookies_str: str, proxies: dict = None)`
- `get_search_keyword(word: str, cookies_str: str, proxies: dict = None)`
- `search_note(query: str, cookies_str: str, page=1, sort_type_choice=0, note_type=0, note_time=0, note_range=0, pos_distance=0, geo=\"\", proxies: dict = None)`
- `search_some_note(query: str, require_num: int, cookies_str: str, sort_type_choice=0, note_type=0, note_time=0, note_range=0, pos_distance=0, geo=\"\", proxies: dict = None)`
- `search_user(query: str, cookies_str: str, page=1, proxies: dict = None)`
- `search_some_user(query: str, require_num: int, cookies_str: str, proxies: dict = None)`
- `get_note_out_comment(note_id: str, cursor: str, xsec_token: str, cookies_str: str, proxies: dict = None)`
- `get_note_all_out_comment(note_id: str, xsec_token: str, cookies_str: str, proxies: dict = None)`
- `get_note_inner_comment(comment: dict, cursor: str, xsec_token: str, cookies_str: str, proxies: dict = None)`
- `get_note_all_inner_comment(comment: dict, xsec_token: str, cookies_str: str, proxies: dict = None)`
- `get_note_all_comment(url: str, cookies_str: str, proxies: dict = None)`
- `get_unread_message(cookies_str: str, proxies: dict = None)`
- `get_metions(cursor: str, cookies_str: str, proxies: dict = None)`
- `get_all_metions(cookies_str: str, proxies: dict = None)`
- `get_likesAndcollects(cursor: str, cookies_str: str, proxies: dict = None)`
- `get_all_likesAndcollects(cookies_str: str, proxies: dict = None)`
- `get_new_connections(cursor: str, cookies_str: str, proxies: dict = None)`
- `get_all_new_connections(cookies_str: str, proxies: dict = None)`
- `get_note_no_water_video(note_id)`
- `get_note_no_water_img(img_url)`

Search filter values below are inferred from the source comments:

- `sort_type_choice`: `0` general, `1` newest, `2` popularity, `3` comments, `4` collects
- `note_type`: `0` all, `1` video, `2` normal note
- `note_time`: `0` all, `1` one day, `2` one week, `3` half year
- `note_range`: `0` all, `1` seen, `2` unseen, `3` followed
- `pos_distance`: `0` all, `1` same city, `2` nearby

## Creator APIs

- `get_topic(keyword, cookies)`
- `get_location_info(keyword, cookies)`
- `get_fileIds(media_type, cookies)`
- `upload_media(path_or_file, media_type, cookies)`
- `query_transcode(video_id, cookies)`
- `encryption(file_id, cookies)`
- `post_note(noteInfo, cookies_str)`
- `get_file_info(file, media_type=\"image\")`
- `get_publish_note_info(page, cookies_str)`
- `get_all_publish_note_info(cookies_str)`

`upload_media` accepts `media_type` of `image` or `video`.

`post_note` payload shape:

```json
{
  "noteInfo": {
    "title": "example title",
    "desc": "example body",
    "postTime": null,
    "location": "Shanghai",
    "type": 0,
    "media_type": "image",
    "topics": ["topic-a", "topic-b"],
    "images": [
      "E:/assets/img-1.jpg",
      "E:/assets/img-2.jpg"
    ]
  },
  "cookies_str": "a1=...; web_session=..."
}
```

Video example:

```json
{
  "noteInfo": {
    "title": "example title",
    "desc": "example body",
    "postTime": null,
    "location": null,
    "type": 0,
    "media_type": "video",
    "topics": [],
    "video": "E:/assets/demo.mp4"
  },
  "cookies_str": "a1=...; web_session=..."
}
```
