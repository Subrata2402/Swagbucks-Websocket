import asyncio
import imp
import aiohttp, json, discord
from discord.ext import commands
stored_ws = {}
from datetime import datetime
import websockets
import db
import config


class SbWebSocket(object):
	
	def __init__(self, client: commands.Bot, username: str = None):
		self.client = client
		self.username = username if username else "User"
		self.ws = None # websocket 
		self.vid = None # current game view id or video id
		self.game_is_active = False # game is live or not
		self.answer = 2
		self.data = None # send answer data
		self.game_id = None # 1254
		self.note = None # 2022-07-06 5:00pm PT
		self.host = "https://api.playswagiq.com/"
		self._host = "https://app.swagbucks.com/"
		self.icon_url = "https://cdn.discordapp.com/attachments/799861610654728212/991317134930092042/swagbucks_logo.png"
		self.headers = {
			"content-type": "application/x-www-form-urlencoded",
			"Host": "api.playswagiq.com",
			"user-agent": "SwagIQ-Android/34 (okhttp/3.10.0)",
			"accept-encoding": "gzip",
			"authorization": "Bearer " + self.get_token()
		}
		
	async def is_expired(self) -> bool:
		"""
		Check if an account is expired and delete it from the database.
		And login again to update the account.
		"""
		data = await self.fetch("POST", "trivia/home", headers = self.headers)
		success = data["success"]
		owner = self.client.get_user(config.OWNER_ID)
		if not success:
			await owner.send(f"{owner.mention}, **{self.username}** account is expired.")
			return await self.send_hook("Auth token has expired!")
		
	def get_token(self) -> str:
		"""
		Get token from database by username.
		"""
		details = db.sb_details.find_one({"username": self.username.lower()})
		if not details:
			print("Not Found any account with this username")
			return "gkdykludkeouflud"
		return details["access_token"]
		
	async def game_details(self) -> None:
		"""
		Get game details.
		"""
		data = await self.fetch("POST", "trivia/join", headers = self.headers)
		if data["success"]:
			self.game_is_active = True
			self.vid = data["viewId"]
			self.game_id = data["episode"]["id"]
			self.note = data["episode"]["title"]
	
	async def get_partner_hash(self, question_number: str) -> str:
		"""
		Get partner hash for confirmation of rejoin in the live game.
		"""
		user_details = db.sb_details.find_one({"username": self.username.lower()})
		token = user_details["token"]
		params = {
			"token": token, "gameID": str(self.game_id),
			"price": "0", "questionNumber": question_number,
			"note": self.note, "useLife": "true", "appid": "37",
			"appversion": "34", "sig": "", # parter hash
		}
		headers = {
			"content-type": "application/x-www-form-urlencoded",
			"Host": "app.swagbucks.com",
			"user-agent": "SwagIQ-Android/34 (okhttp/3.10.0);Realme RMX1911",
			"accept-encoding": "gzip",
		}
		data = await self.fetch("POST", "?cmd=apm-70", headers = headers, params = params, host = "host")
		await self.send_hook("\n```\n{}\n```".format(data))
		return data.get("sig")

	
	async def fetch(self, method = "GET", function = "", headers = None, params = None, data = None, host = None) -> dict:
		"""
		Request Swagbucks to perform the action.
		"""
		host = self._host if host else self.host
		async with aiohttp.ClientSession() as client_session:
			response = await client_session.request(method = method, url = host + function, params = params, headers = headers, data = data)
			content = await response.text()
			return json.loads(content)
	
	async def send_answer(self, qid: str, aid: str) -> None:
		"""
		Send answer to the game.
		"""
		params = {
			"vid": self.vid, "qid": qid, "aid": aid, "timeDelta": "5000"
		}
		self.data = await self.fetch("POST", "trivia/answer", headers = self.headers, params = params)
		await self.send_hook("\n```\n{} | {}\n```".format(self.data, self.username))
	
	async def confirm_rebuy(self, question_number: str) -> None:
		"""
		If any question is wrong then we are eliminated.
		For come back and join again to the game we use a rejoin.
		To use this function we can send a rejoin. 
		"""
		if self.data.get("whenIncorrect"):
			allow_rebuy = self.data["whenIncorrect"]["allowRebuy"]
		else:
			return None
		if allow_rebuy:
			partner_hash = await self.get_partner_hash(question_number)
			if not partner_hash: return 
			post_data = f"vid={self.vid}&useLife=true&partnerHash={partner_hash}"
			data = await self.fetch("POST", "trivia/rebuy_confirm", headers = self.headers, data = post_data)
			await self.send_hook("\n```\n{} | {}\n```".format(data, self.username))
			
	async def confirm_sb(self) -> None:
		"""
		If lost the game, Swagbucks asked to confirm to take bonus sb.
		Then you need confirm sb to credited sb in Swagbucks wallet.
		"""
		post_data = f"vid={self.vid}"
		data = await self.fetch("POST", "trivia/confirm_sb", headers = self.headers, data = post_data)
		await self.send_hook("\n```\n{} | {}\n```".format(data, self.username))
	
	async def complete_game(self) -> None:
		"""
		After end of the game check the details of winnings 
		and how many sb earn from the live game.
		"""
		post_data = f"vid={self.vid}"
		data = await self.fetch("POST", "trivia/complete", headers = self.headers, data = post_data)
		await self.send_hook("\n```\n{} | {}\n```".format(data, self.username))
		confirm = data["confirm"]
		winner = data["winner"]
		if confirm and not winner:
			await self.confirm_sb()

	
	async def get_ws(self) -> None:
		"""
		Get Websocket.
		"""
		self.ws = stored_ws.get(self.username)

	async def close_ws(self) -> None:
		"""
		Close Websocket.
		"""
		await self.get_ws()
		if not self.ws:
			await self.send_hook("**Websocket Already Closed!**")
		else:
			if self.ws.closed:
				return await self.send_hook("**Websocket Already Closed!**")
			await self.ws.close()
			await self.send_hook("**Websocket Closed!**")
			
	async def send_hook(self, content = "", embed = None) -> None:
		"""
		Send message with Discord channel Webhook.
		"""
		web_url = config.WEBHOOK_URL
		async with aiohttp.ClientSession() as session:
			webhook = discord.Webhook.from_url(web_url, adapter=discord.AsyncWebhookAdapter(session))
			await webhook.send(content = content, embed = embed, username = self.client.user.name, avatar_url = self.client.user.avatar_url)
			
	
	async def connect_websocket(self) -> None:
		"""
		Connect websocket to join Swagbucks Live game and play.
		"""
		await self.is_expired()
		await self.game_details()
		if not self.game_is_active:
			await self.send_hook("```\nGame is not active! Username : {}\n```".format(self.username))
			await asyncio.sleep(300)
			return await self.connect_websocket()
		socket_url = "wss://api.playswagiq.com/sock/1/game/{}".format(self.vid)
		self.ws = await websockets.connect(socket_url, extra_headers = self.headers, ping_interval = 15)
		stored_ws[self.username] = self.ws
		question_number = 0
		await self.send_hook("Websocket successfully connected! Username : {}".format(self.username))
		async for message in self.ws:
			message_data = json.loads(message)
			if message_data["code"] == 41:
				question_number = message_data["question"]["number"]
				total_question = message_data["question"]["totalQuestions"]
				question_id = message_data["question"]["idSigned"]
				answer_ids = [answer["idSigned"] for answer in message_data["question"]["answers"]]
				embed = discord.Embed(title = f"Question {question_number} out of {total_question}", url = "https://google.com")
				await self.send_hook(embed = embed)
				def check(message):
					return message.author.id == config.USER_ID and message.channel.id == config.CHANNEL_ID
				while True:
					try:
						user_input = await self.client.wait_for("message", timeout = 10.0, check = check)
						if user_input.content.strip() not in ["1", "2", "3"]:
							continue
						self.answer = int(user_input.content.strip())
					except Exception as e:
						await self.send_hook("You failed to send your answer within time or something went wrong. Username : {}\n```\n{}\n```".format(self.username, e))
						self.answer  = 2
					answer_id = answer_ids[self.answer - 1]
					break
				await self.send_answer(question_id, answer_id)
					
			if message_data["code"] == 42:
				ansid = message_data["correctAnswerId"]
				for index, answer in enumerate(message_data["answerResults"]):
					if answer["answerId"] == ansid:
						ans_num = index + 1
				
				embed = discord.Embed(title = f"Correct Answer : {ans_num}")
				await self.send_hook(embed = embed)
				
				# if self.answer != ans_num:
				# 	await self.confirm_rebuy(str(question_number))
					
			if message_data["code"] == 49:
				await self.complete_game()
				await asyncio.sleep(900)
				if not self.ws:
					return await self.connect_websocket()
				else:
					if self.ws.closed:
						return await self.connect_websocket()
					await self.ws.close()
					await self.send_hook("**Websocket Closed!**")
					return await self.connect_websocket()
				
				
class SwagbucksLive(SbWebSocket):
	
	def __init__(self, client: commands.Bot, username: str = None):
		super().__init__(client, username)
		self.client = client

	async def login(self, email_id: str, password: str, get_token: str = None) -> None:
		"""
		Login to Swagbucks with username and password
		and save login credentials to database.
		"""
		params = {
			"emailAddress": email_id,
			"pswd": password,
			"sig": "", # "sig": "https://www.swagbucks.com/?f=1",
			"appversion": "34",
			"appid": "37"
		}
		headers = {
			"content-type": "application/x-www-form-urlencoded",
			"Host": "app.swagbucks.com",
			"user-agent": "SwagIQ-Android/34 (okhttp/3.10.0);Realme RMX1911",
			"accept-encoding": "gzip",
			# "authorization": self.get_token()
		}
		data = await self.fetch("POST", "?cmd=apm-1", headers = headers, params = params, host = "host")
		if data["status"] != 200:
			return await self.send_hook("```\n{}\n```".format(data))
		username = data["user_name"]
		user_id = data["member_id"]
		check = db.sb_details.find_one({"user_id": user_id})
		if check: return await self.send_hook("This account already exists in bot.")
		token = data["token"]
		sig = data["sig"]
		
		
		data = f"_device=f6acc085-c395-4688-913f-ea2b36d4205f&partnerMemberId={user_id}&partnerUserName={username}&verify=false&partnerApim=1&partnerHash={sig}"
		data = await self.fetch("POST", "auth/token", headers = headers, data = data)
		access_token = data["accessToken"]
		refresh_token = data["refreshToken"]
		if get_token: return access_token
		db.sb_details.insert_one({
			"user_id": user_id, "username": username.lower(),
			"access_token": access_token, "refresh_token": refresh_token,
			"token": token, "sig": sig,
			"email_id": email_id, "password": password
		})
		await self.send_hook("Successfully login to Swagbucks. Username : `{}`".format(username))
	
	async def update_account(self, username: str) -> None:
		"""
		If the bearer token is expired then refresh the token and update account.
		"""
		details = db.sb_details.find_one({"username": username})
		if not details:
			return await self.send_hook("Not found with this username.")
		user_id = details["user_id"]
		sig = details["sig"]
		headers = {
			"content-type": "application/x-www-form-urlencoded",
			"Host": "app.swagbucks.com",
			"user-agent": "SwagIQ-Android/34 (okhttp/3.10.0);Realme RMX1911",
			"accept-encoding": "gzip",
			# "authorization": self.get_token()
		}
		data = f"_device=f6acc085-c395-4688-913f-ea2b36d4205f&partnerMemberId={user_id}&partnerUserName={username}&verify=false&partnerApim=1&partnerHash={sig}"
		data = await self.fetch("POST", "auth/token", headers = headers, data = data)
		access_token = data["accessToken"]
		refresh_token = data["refreshToken"]
		update = {"access_token": access_token, "refresh_token": refresh_token}
		db.sb_details.update_one({"user_id": user_id}, {"$set": update})
		await self.send_hook("Account successfully updated!")
	
	async def account_details(self, username: str, sb: bool = False) -> None:
		"""
		Get account details.
		"""
		user_details = db.sb_details.find_one({"username": username.lower()})
		if not user_details:
			return await self.send_hook("No account found with name `{}`".format(username))
		token = user_details["token"]
		params = {
			"token": token, "checkreferral": "false",
			"appid": "37", "appversion": "34"
		}
		headers = {
			"content-type": "application/x-www-form-urlencoded",
			"Host": "app.swagbucks.com",
			"user-agent": "SwagIQ-Android/34 (okhttp/3.10.0);Realme RMX1911",
			"accept-encoding": "gzip",
			# "authorization": self.get_token()
		}
		data = await self.fetch("POST", "?cmd=apm-3", headers = headers, params = params, host = "host")
		if data["status"] != 200:
			return await self.send_hook("```\n{}\n```".format(data))
		if sb: return data.get("swagbucks")
		description = f"```\n" \
				f"• User Id             ::  {data['member_id']}\n" \
				f"• Email Verified      ::  {data['email_verified']}\n" \
				f"• Rejoins (Lives)     ::  {data['lives']}\n" \
				f"• Username            ::  {data['user_name']}\n" \
				f"• Swagbucks (SB)      ::  {data.get('swagbucks')}\n" \
				f"• Re-Verification     ::  {data['require_reverification']}\n" \
				f"• Profile Complete    ::  {data['profile_complete']}\n" \
				f"• OTP Verified        ::  {data['otp_verified']}\n" \
				f"• Member Status       ::  {data['member_status']}\n" \
				f"• Pending Earnings    ::  {data['pending_earnings']}\n" \
				f"• Registered Date     ::  {data['registered_date']}\n" \
				f"• Lifetime Earnings   ::  {data['lifetime_earnings']}\n```"
		await self.send_hook(description)
		
	async def show_details(self) -> None:
		"""
		Get the details of the current game show.
		"""
		await self.is_expired()
		data = await self.fetch("POST", "trivia/home", headers = self.headers)
		prize = data["episode"]["grandPrizeDollars"]
		time = data["episode"]["start"]
		embed=discord.Embed(title = "__SwagIQ Next Show Details !__", description=f"• Show Name : Swagbucks Live\n• Show Time : <t:{time}>\n• Prize Money : ${prize}", color = discord.Colour.random())
		embed.set_thumbnail(url = self.icon_url)
		embed.set_footer(text = "Swagbucks Live")
		embed.timestamp = datetime.utcnow()
		await self.send_hook(embed = embed)