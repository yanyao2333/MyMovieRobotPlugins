from plugins.BilibiliDownloader.core import save_video_modes

SAVE_MODE = save_video_modes.SaveVideoMode.NORMAL_STYLE

def get_config(save_mode: save_video_modes.SaveVideoMode):
    """获取配置信息"""
    global SAVE_MODE
    SAVE_MODE = save_mode



async def