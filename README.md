### Swagbucks Websocket
It is a websocket of Swagbucks Live game. To use this websocket you can play live game with this bot. You can play multiple accounts with this websocket. But don't run 4-5 accounts in one invironment. If run chance to get ban account.

+ To run this bot you need to follow these steps :
  - Create a mongo db account if not
  - Put all details in [config.py](https://github.com/Subrata2402/Swagbucks-Websocket/blob/main/config.py) file
  - Put usernames in 12 no. line of [swagbucks.py](https://github.com/Subrata2402/Swagbucks-Websocket/blob/b4c9a07074e7987cbe0ccad057e186a3fad73ae2/swagbucks.py#L12)
  - Login may be not working so you should insert data in mongo db to this format

  ```
  {
      "user_id": 123652319,
      "username": "baldric3250schne",
      "access_token": "COjBzVzAFpEnZ-Q1R-J4tT5DaUrq6kfnrJ6OfUe0m20C9J76CPW-Mp48D-nLjAdQ0ukrhm…",
      "refresh_token": "COjBzS8lDa2uQnM6j7u3WamSovfWzY_2BlsQ8h-5_KaKG7HAkpYDspCbaRGDgSOqOKNmKz…",
      "token": "123652319~0dbd3f436469290e4d44be5b831e9963~mpODKaqKxwH6",
      "sig": "ea65dd733d983732775be55946e950a33bdb487bfbc57756c719b9843edc0c14",
      "email_id": "baldric3250schneider@gmail.com",
      "password": "Subrata@2001"
  }
  ```
