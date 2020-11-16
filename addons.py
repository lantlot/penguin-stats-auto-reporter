import json

import mitmproxy.http
import requests
from mitmproxy import ctx

upload_url = 'https://penguin-stats.io/PenguinStats/api/v2/report'


class Reporter:
    def __init__(self):
        userid = '91528942'
        self.session = requests.Session()
        # 暂时从浏览器里抓到头来模拟浏览器提交
        self.session.headers = {
            'content-type': 'application/json;charset=UTF-8',
            'cookie': '__cfduid=d8ce585ee88947d8468cbfc8c5b19a8c51604338917; _ga=GA1.2.1995108991.1604338921; _gid=GA1.2.884072268.1605353302; userID=' + userid + '; crisp-client%2Fsession%2F2aa1bf4c-8c34-4028-9e1c-ca1f6c330779=session_f8fa504c-43c8-4e39-bbfb-f67b09271b04; _gat=1'}

    class Drop:
        def __init__(self, drop_type, item_id, quantity):
            self.dropType = drop_type
            self.itemId = item_id
            self.quantity = quantity

    class JsonCustomEncoder(json.JSONEncoder):
        def default(self, field):
            if isinstance(field, Reporter.Drop):
                return field.__dict__
            else:
                return json.JSONEncoder.default(self, field)

    def http_connect(self, flow: mitmproxy.http.HTTPFlow):
        ctx.log.info(flow.request.host)
        if flow.request.host == "ak-gs-localhost.hypergryph.com":
            flow.request.host = "ak-gs.hypergryph.com"
            flow.request.port = 8443
        elif flow.request.host == "ak-as-localhost.hypergryph.com":
            flow.request.host = "ak-as.hypergryph.com"
            flow.request.port = 9443

    def response(self, flow: mitmproxy.http.HTTPFlow):
        if flow.request.host == "ak-gs.hypergryph.com" and flow.request.path.startswith("/quest/battleFinish"):
            rewards = json.loads(flow.response.get_text())
            # 不是三星通关 返回报文里似乎没有评级的返回
            if rewards['expScale'] != 1.2:
                return
            # 首次通关也不进行上报
            if rewards['firstRewards']:
                return
            # stageId 在战斗结束的报文里没有显示返回，只能取用户数据变更里变更的关卡状态 战斗结束一般来说只会变化战斗的那个关卡
            stage_id = list(rewards['playerDataDelta']['modified']['dungeon']['stages'].keys())[0]
            # 只上报 主线 活动 芯片 周常本 如有变化可以修改这里
            if not str.startswith(stage_id, ('main', 'act', 'pro', 'wk')):
                return
            drop_list = []
            for item in rewards['additionalRewards']:
                if item['count'] != 0:
                    drop_list.append(Reporter.Drop('EXTRA_DROP', item['id'], int(item['count'])))
            for item in rewards['unusualRewards']:
                if item['count'] != 0:
                    drop_list.append(Reporter.Drop('SPECIAL_DROP', item['id'], int(item['count'])))
            for item in rewards['rewards']:
                # 红票及龙门币不提交
                if item['count'] != 0 and item['id'] != '4001' and item['id'] != '4006':
                    drop_list.append(Reporter.Drop('NORMAL_DROP', item['id'], int(item['count'])))
            for item in rewards['furnitureRewards']:
                if item['count'] != 0:
                    drop_list.append(Reporter.Drop('FURNITURE', 'furni', int(1)))

            request = json.dumps({'server': 'CN', 'source': 'frontend-v2', 'version': 'v3.3.6', 'drops': drop_list,
                                  'stageId': stage_id}, cls=Reporter.JsonCustomEncoder)
            ctx.log.info(request)
            ret = self.session.post(upload_url, data=request)
            ctx.log.info(ret.text)


addons = [
    Reporter()
]
