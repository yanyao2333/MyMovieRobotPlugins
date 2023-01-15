"""查询追更up主更新情况"""

class ListenUploadVideo:
    """查询用户是否发新视频，配合定时任务使用"""

    def __init__(
            self, uid=123, if_get_character=False, media_path=None, emby_persons_path=None
    ):
        self.uid = uid
        self.if_get_character = if_get_character
        self.media_path = media_path
        self.emby_persons_path = emby_persons_path

    async def listen_no_pages_video_new(self):
        """
        官方没有给查看分p上传时间的接口，遇到分p视频直接ignore，并通知用户自行下载
        so bilibili fuck you!
        """
        # _LOGGER.info(f"开始查询用户 {self.uid} 是否上传新视频")
        if not os.path.exists(f"{local_path}/listen_up.json"):
            await self.save_data(f"{local_path}/listen_up.json")
        elif not await self.verify_json(f"{local_path}/listen_up.json"):
            await self.save_data(f"{local_path}/listen_up.json")
        await self.load_data(f"{local_path}/listen_up.json")
        if not await self.query_data(uid=self.uid):
            await self.modify_data(
                uid=self.uid, time=int(datetime.datetime.now().timestamp()), mode="add"
            )
        all_video = await user.User(credential=credential, uid=self.uid).get_videos(
            ps=50
        )
        video_list = all_video["list"]["vlist"]
        for v in reversed(video_list):
            if await self.query_data(self.uid) is not None and self.compare_time(
                    v["created"], await self.query_data(self.uid)
            ):
                t = await self.query_data(self.uid)
                video_info = await video.Video(bvid=v["bvid"]).get_info()
                if len(await video.Video(bvid=v["bvid"]).get_pages()) > 1:
                    _LOGGER.info(f"用户{self.uid}发布了分p视频，忽略")
                    await self.modify_data(self.uid, v["created"], "update")
                    Notify(video_info).send_pages_video_notify()
                    await self.save_data(f"{local_path}/listen_up.json")
                    continue
                else:
                    _LOGGER.info(f"用户 {self.uid} 发布了新视频：{video_info['title']}  开始下载")
                    res = await BilibiliProcess(
                        v["bvid"],
                        if_get_character=self.if_get_character,
                        media_path=self.media_path,
                        emby_persons_path=self.emby_persons_path,
                    ).process()
                    if res:
                        await self.modify_data(self.uid, v["created"], "update")
                        await self.save_data(f"{local_path}/listen_up.json")
                    continue
            elif await self.query_data(self.uid) is None:
                await self.modify_data(self.uid, v["created"], "add")
                await self.save_data(f"{local_path}/listen_up.json")
                continue
            elif not self.compare_time(v["created"], await self.query_data(self.uid)):
                await self.save_data(f"{local_path}/listen_up.json")
                continue