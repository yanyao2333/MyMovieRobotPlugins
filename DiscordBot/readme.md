# DiscordBot

-----

## 频道、服务器id

方法一：去设置->打开开发者模式->右键频道或服务器->复制id  
具体操作：![打开开发者模式](images/打开开发者模式.png)![频道id](images/复制频道id.png)![服务器id](images/复制服务器id.png)

方法二：右键频道复制链接（例：https://discord.com/channels/12345678900/123456789123）第一串数字就是服务器id，第二串数字就是频道id

-----

## 创建bot

https://discord.com/developers/applications 创建应用并进入，接着点Bot -> Add Bot -> Reset
Token，复制出现的一串token即可（别忘了在bot页打开MESSAGE CONTENT INTENT权限）

bot页配置：![配置](images/MESSAGE_CONTENT_INTENT.png)

-----

## 添加bot到服务器

把client_id替换成你的，然后访问即可添加bot到服务器

https://discord.com/api/oauth2/authorize?client_id=<填自己的>&permissions=0&scope=bot%20applications.commands

client id获取：
![client_id](images/clientid.png)

-----

## 使用方法

输入 / 会显示所有命令，自行选择即可

-----

## Q&A

```diff
- 输入命令后出现任何报错都请先重试一两次，discord会偶尔抽风，如果还不行再问！！！
```

1. 日志停留在`DiscordBot - INFO: logging in using static token`，没有出现`已登录xxx#xxxx`，bot没有上线，且下面没有其他报错
   - 检查网络是否正常
2. 报错`discord.errors.NotFound： 404 Not Found（error code： 10062）：Unknown interaction`
   - 再试一次即可（本质上还是网络不好，新版本已经尝试修复此问题）
3. 报错`The specified option value is already used`
   - 再试一次基本就没有问题了
   - 检查mr是否在正常运行
