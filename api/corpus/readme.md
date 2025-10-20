语料库服务说明文档
1. 找到 window 路径下 hosts 配置文件，通常在C:\WINDOWS\system32\drivers\etc目录下
[img.png](img.png)
2. 用记事本或其他软件以管理员权限打开 C:\WINDOWS\system32\drivers\etc\hosts 文件, 在最后一行添加 81.70.124.65 corpus.chineseplus.net 
[img_1.png](img_1.png)
3. linux 配置 hosts 同理
4. 配置完毕运行search_query.py查询即可
5. 服务接口示例
curl -X POST -d "{'query':'办法{}Context(100)'}" -H "Content-Type: application/json; charset=UTF-8" https://corpus.chineseplus.net/api/v1/search/edu

Method         POST
Header         Content-Type: application/json; charset=UTF-8
Request Body   {'query': string}