import pypresence
import requests
import configparser
import argparse
from pythonosc import dispatcher as dp
from pythonosc import osc_server as oscsvr
from pythonosc import udp_client as udpc
import datetime

print("起動中です...")


def debugprint(content):
    if cfg["Client"]["Debug"]:
        print(content)


# cfgを読み込む為
cfg = configparser.ConfigParser()
cfg.read("./config.ini", encoding="utf-8")
debugprint("[debug] configparser module has been successfully loaded.")

# authに必要な変数
client_id = int(cfg["Client"]["Client_id"])
api_endpoint = "https://discord.com/api/v10"
client_secret = cfg["Client"]["Client_secret"]
redirect_url = "https://localhost:65535"


# 無い可能性があるやつ このコメントは後で消す
access_token = cfg["Client"]["Access_token"]
debugprint("[debug] The variable was successfully created.")

# RPCオブジェクト
RPC = pypresence.Client(client_id)
RPC.start()
debugprint("[debug] RPC object was successfully created.")

# authorization codeをaccess tokenに変換する。
def exchange_code(code):
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_url": redirect_url,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post("%s/oauth2/token" % api_endpoint, data=data, headers=headers)
    debugprint("[debug] code was successfully converted.")
    r.raise_for_status()
    return r.json()["access_token"]


# Access tokenが存在しない場合は作成。
def create_access_token():
    response = RPC.authorize(
        client_id=client_id, scopes=["rpc", "rpc.voice.write", "rpc.voice.read"]
    )
    debugprint("[debug] Authorize request completed successfully.")
    print(
        f"Discordとの認証に成功しました。1週間後({datetime.datetime.now() + datetime.timedelta(days=7)})に、再度認証が必要になります。"
    )
    return exchange_code(response["data"]["code"])


# 既存のアクセストークンを使用して、RPCと接続できるか確認。
def check_access_token_alive(access_token):
    try:
        RPC.authenticate(access_token)
        debugprint(
            "[debug] Connection to RPC successfully completed with existing access token."
        )
        return True
    except pypresence.exceptions.DiscordError:
        # Invalid access tokenが発生した場合
        debugprint("[debug] Access token was invalid.")
        return False
    except Exception as e:
        # それ以外の例外が発生した場合
        debugprint(
            "[debug] An unexpected error occurred in function check_access_token_alive"
        )
        print(e)
        return False


def listen_server_create():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1", help="Listen")
    parser.add_argument("--port", type=int, default="9001", help="Listen")
    args = parser.parse_args()
    dispatcher = dp.Dispatcher()
    dispatcher.map("/avatar/parameters/Discord*", change_settings)
    return oscsvr.ThreadingOSCUDPServer((args.ip, args.port), dispatcher)


def status_sync():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1", help="Sync")
    parser.add_argument("--port", type=int, default=9000, help="Sync")
    args = parser.parse_args()
    client = udpc.SimpleUDPClient(args.ip, args.port)
    voice_settings = RPC.get_voice_settings()["data"]
    client.send_message("/avatar/parameters/DiscordMicMute", voice_settings["mute"])
    client.send_message("/avatar/parameters/DiscordSpeakerMute", voice_settings["deaf"])


def Mute():
    RPC.set_voice_settings(mute=True)
    debugprint("[debug] Discord mic was set to mute using the controls within VRChat.")
    status_sync()
    debugprint("[debug] Status synchronization completed successfully.")


def Unmute():
    RPC.set_voice_settings(mute=False)
    debugprint(
        "[debug] Discord mic was set to unmute using the controls within VRChat."
    )
    status_sync()
    debugprint("[debug] Status synchronization completed successfully.")


def SpeakerMute():
    RPC.set_voice_settings(deaf=True)
    debugprint("[debug] Discord mic was set to mute using the controls within VRChat.")
    status_sync()
    debugprint("[debug] Status synchronization completed successfully.")


def SpeakerUnmute():
    RPC.set_voice_settings(deaf=False)
    debugprint(
        "[debug] Discord mic was set to unmute using the controls within VRChat."
    )
    status_sync()
    debugprint("[debug] Status synchronization completed successfully.")


def change_settings(address, value):
    debugprint(f"[debug] {address}, send value: {value}")
    if address == "/avatar/parameters/DiscordMicMute" and value == True:
        Mute()
        print(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] VRChat内での操作で、Discordのマイクをミュートに設定しました。"
        )

    elif address == "/avatar/parameters/DiscordMicMute" and value == False:
        Unmute()
        print(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] VRChat内での操作で、Discordのマイクミュートを解除しました。"
        )

    elif address == "/avatar/parameters/DiscordSpeakerMute" and value == True:
        SpeakerMute()
        print(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] VRChat内での操作で、Discordのスピーカーミュートを設定しました。"
        )

    elif address == "/avatar/parameters/DiscordSpeakerMute" and value == False:
        SpeakerUnmute()
        print(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] VRChat内での操作で、Discordのスピーカーミュートを解除しました。"
        )

    else:
        print(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 予期しない値を受信しました。DiscordMutedのParametersがBoolになっていない可能性があります。"
        )


def main():
    global access_token
    # Access tokenがiniに存在しない場合、作成と上書き
    if not access_token:
        access_token = create_access_token()
        cfg["Client"]["Access_token"] = access_token
        with open("config.ini", "w") as f:
            cfg.write(f)

        debugprint("[debug] Creation of Access token completed successfully.(None)")

    # Access tokenが死んでる場合、作成
    if check_access_token_alive(access_token):
        debugprint("[debug] Access token is valid.")

    else:
        debugprint("[debug] Access token is invalid.")

        access_token = create_access_token()
        cfg["Client"]["Access_token"] = access_token
        with open("config.ini", "w") as f:
            cfg.write(f)

        debugprint("[debug] Creation of Access token completed successfully.(Invalid)")

        RPC.authenticate(access_token)
        debugprint(
            "[debug] Connection to RPC successfully completed with existing access token."
        )
    debugprint("[debug] Access token successfully identified.")

    # 受信サーバーの作成
    server = listen_server_create()

    debugprint("[debug] Serving on {}".format(server.server_address))
    debugprint("[debug] The OSC receiving server was successfully created.")
    print("ソフトの準備ができました。VRChat内よりDiscordのマイクを設定できます。")

    status_sync()
    debugprint("[debug] Status synchronization completed successfully.")

    server.serve_forever()


if __name__ == "__main__":
    debugprint("[debug] Running normally.")
    main()
