import discord
from Websocket.swagbucks_ws import SbWebSocket, SwagbucksLive
from discord.ext import commands
import db
import config

class SwagbucksTrivia(commands.Cog, SwagbucksLive):
	
	def __init__(self, client: commands.Bot):
		super().__init__(client)
		self.client = client
		self.usernames = [] # list of username of swagbucks account  

	@commands.Cog.listener()
	async def on_ready(self):
		print(f"{self.client.user.name} is Ready!")
		game = discord.Game("Swagbucks Live")
		await self.client.change_presence(status=discord.Status.dnd, activity=game)
		
		# play swagbucks account automatically
		# if you want start manualy then comment out this 3 lines
		for username in self.usernames:
			ws = SbWebSocket(self.client, username)
			self.client.loop.create_task(ws.connect_websocket())


	@commands.command()
	@commands.is_owner()
	async def sbstart(self, ctx: commands.Context, username: str = None):
		"""
		Check and open a websocket by username. 
		"""
		if not username:
			return await ctx.send("Uername is required!")
		ws = SbWebSocket(self.client, username)
		await ws.get_ws()
		if ws.ws:
			if ws.ws.open:
				return await ws.send_hook("Websocket Already Opened!")
		await ws.send_hook("Websocket Connecting...")
		await ws.connect_websocket()
		
		
	@commands.command()
	@commands.is_owner()
	async def sbclose(self, ctx: commands.Context, username: str = None):
		"""
		Close a websocket by username.
		"""
		ws = SbWebSocket(self.client, username.lower())
		await ws.close_ws()
	
	# @commands.command()
	# @commands.is_owner()
	# async def sblogin(self, ctx: commands.Context, email_id: str = None, password: str = None):
	# 	"""
	# 	Login a Swagbucks account and stored some required details in the database.
	# 	"""
	# 	if not email_id or not password:
	# 		return await ctx.send("Username or Password is required to login to Swagbucks.")
	# 	await self.login(email_id, password)
		
	@commands.command()
	@commands.is_owner()
	async def sbupdate(self, ctx: commands.Context, username: str = None):
		"""
		If account is expire then this command will delete the stored account details
		and login again to update account.
		"""
		if not username:
			return await ctx.send("Required username to update of Swagbucks account.")
		await self.update_account(username)

	@commands.command()
	@commands.is_owner()
	async def adddata(self, ctx: commands.Context, *, args: str):
		data = args.split(", ")
		insert_data = {
				"user_id": data[0],
				"username": data[1],
				"access_token": data[2],
				"refresh_token": data[3],
				"token": data[4],
				"sig": data[5],
				"email_id": data[6],
				"password": data[7]
			}
		db.sb_details.insert_one(insert_data)
		await ctx.send("Success!")

		
	@commands.command()
	@commands.is_owner()
	async def sbdetails(self, ctx: commands.Context, username: str = None):
		"""
		Get stats details of a Swagbucks account.
		"""
		if not username:
			return await ctx.send("Required username to get details of Swagbucks account.")
		await self.account_details(username.lower())
		
	
	@commands.command(name="sbaccounts", aliases=["sbacc"])
	@commands.is_owner()
	async def sbaccounts(self, ctx: commands.Context):
		"""
		Get all accounts username, stored in the database.
		"""
		accounts = list(db.sb_details.find())
		description = ""
		for index, data in enumerate(accounts):
			description += "{}{} - {}\n".format(0 if index+1 < 10 else "", index+1, data["username"])
		if not accounts:
			return await ctx.send("No accounts found.")
		await ctx.send("```\n{}\n```".format(description))

	@commands.command(name="sbbalance", aliases=["sbbal"])
	@commands.is_owner()
	async def sbbalance(self, ctx: commands.Context):
		"""
		Get all accounts Swagbucks details, stored in the database.
		"""
		accounts = list(db.sb_details.find())
		description = ""
		for index, data in enumerate(accounts):
			sb = await self.account_details(data["username"].lower(), True)
			description += "{}{} - {} - {} SB\n".format(0 if index+1 < 10 else "", index+1, data["username"], sb)
		if not accounts:
			return await ctx.send("No accounts found.")
		await ctx.send("```\n{}\n```".format(description))
    
		
	@commands.command()
	@commands.is_owner()
	async def nextshow(self, ctx: commands.Context):
		"""
		Get Swagbucks Live next show details.
		"""
		username = list(db.sb_details.find())[0]["username"]
		ws = SwagbucksLive(self.client, username)
		await ws.show_details()
		

intents = discord.Intents.all()
client = commands.Bot(command_prefix = ">", intents = intents, strip_after_prefix = True, case_insensitive = True)
client.add_cog(SwagbucksTrivia(client))
client.run(config.BOT_TOKEN)
