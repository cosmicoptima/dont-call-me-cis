import asyncio
from collections import defaultdict
from dataclasses import dataclass
import discord
from dotenv import load_dotenv
import openai
from os import environ
import random
import replicate
import requests
import wonderwords

load_dotenv()

openai.api_key = environ["OPENAI_API_KEY"]
r = wonderwords.RandomWord()

sd = replicate.models.get("cjwbw/stable-diffusion-v2")


@dataclass
class Message:
    author: str
    content: str


messages = defaultdict(list)


def messages_to_prompt(channel, adj1, adj2):
    body = "\n".join(f"{msg.author}: {msg.content}" for msg in messages[channel][-25:])

    return "The following is a chatlog. The user 'don't call me cis' is insane and always replies in an unhinged manner.\n\n" + body + f"\n(The following message is all lowercase. Here, dcmc shifts tone and vocabulary completely and instead exposes themselves as remarkably {adj1} and somewhat {adj2})\ndon't call me cis:"


def generate_adjective():
    word = r.word(include_parts_of_speech=["adjective"])
    while word == "black": # leads to racism
        word = r.word(include_parts_of_speech=["adjective"])
    
    return word


def generate_art_style():
    p = random.random()
    if p < 0.4:
        return "digital art"
    elif p < 0.6:
        return "a painting"
    elif p < 0.8:
        return "an anime drawing"
    else:
        return "a 4k award-winning photograph"


class MyClient(discord.Client):
    adj1 = generate_adjective()
    adj2 = generate_adjective()
    
    async def avi(self):
        output_url = sd.predict(prompt=f"{generate_art_style()} of a person's face who is {self.adj1} and {self.adj2}")[0]
        image = requests.get(output_url).content
        await self.user.edit(avatar=image)

    async def on_ready(self):
        await self.avi()

    async def on_message(self, message):
        messages[message.channel].append(Message(message.author.name, message.content))

        if message.content == "!dcmc acid":
            self.adj1 = generate_adjective()
            self.adj2 = generate_adjective()
            await self.avi()
            messages[message.channel] = []
            return

        if message.content == "!dcmc amnesia":
            messages[message.channel] = []
            return

        if message.content == "!dcmc avi":
            await self.avi()
            return

        if "dcmc" in message.content:
            p = 0.9
        else:
            p = 0.1

        if random.random() < p:
            async with message.channel.typing():
                completion = openai.Completion.create(
                    engine="text-curie-001",
                    prompt=messages_to_prompt(message.channel, self.adj1, self.adj2),
                    max_tokens=256,
                    temperature=1,
                    stop=["\n"],
                    frequency_penalty=0.5,
                    presence_penalty=0.5,
                )
                await asyncio.sleep(len(completion.choices[0].text) / 10)
                await message.channel.send(completion.choices[0].text)

                print(f"posted - {completion.choices[0].text[:10]}... {self.adj1} {self.adj2}")

        if random.random() < 0.02:
            self.adj1 = generate_adjective()
        if random.random() < 0.1:
            self.adj2 = generate_adjective()


intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(environ["DISCORD_TOKEN"])
