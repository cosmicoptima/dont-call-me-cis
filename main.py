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
from sys import argv
import wonderwords

load_dotenv()

openai.api_key = environ["OPENAI_API_KEY"]
sd = replicate.models.get("cjwbw/stable-diffusion-v2")


@dataclass
class Message:
    author: str
    content: str


messages = defaultdict(list)


def generate_adjective():
    generator = wonderwords.RandomWord()

    word = generator.word(include_parts_of_speech=["adjective"])
    while word == "black":  # leads to racism
        word = generator.word(include_parts_of_speech=["adjective"])

    return word


class MyClient(discord.Client):
    adj1 = generate_adjective()
    adj2 = generate_adjective()

    shushed = False

    async def set_avi(self):
        output_url = sd.predict(
            prompt=f"digital art of a person's face, Discord profile picture, {self.adj1} style, {self.adj2} style",
            negative_prompt="ugly",
        )[0]
        image = requests.get(output_url).content
        await self.user.edit(avatar=image)

    async def set_name(self):
        completion = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Select a short phrase that DCMC would stand for. It should be a person's name, and indirectly allude to them being remarkably {self.adj1}, and also somewhat {self.adj2}.",
            temperature=0.65,
        )
        name = completion.choices[0].text.strip().lower()
        name = "".join(c for c in name if c != ".")
        name = " ".join(name.split())

        members = self.get_all_members()
        for member in members:
            if member.id == self.user.id:
                await member.edit(nick=name[:32])

        self.name = name

    def prompt(self, channel):
        body = "\n".join(
            f"{msg.author}: {msg.content}" for msg in messages[channel][-25:]
        )

        return (
            "The following is a chatlog. The user '{self.name}' is insane and always replies in an unhinged manner.\n\n"
            + body
            + f"\n(The following message is {'very short and ' if random.random() < 0.8 else ''}all lowercase. Here, {self.name} shifts tone and vocabulary completely and instead exposes themselves as remarkably {self.adj1} and somewhat {self.adj2})\n{self.name}:"
        )

    async def on_ready(self):
        if not "--no-avi" in argv:
            await self.set_avi()
        if not "--no-name" in argv:
            await self.set_name()

    async def on_message(self, message):
        messages[message.channel].append(Message(message.author.name, message.content))

        if message.content == "!dcmc acid":
            self.adj1 = generate_adjective()
            self.adj2 = generate_adjective()
            await self.set_avi()
            await self.set_name()
            messages[message.channel] = []
            return

        if message.content == "!dcmc amnesia":
            messages[message.channel] = []
            return

        if message.content == "!dcmc avi":
            await self.set_avi()
            return

        if message.content == "!dcmc name":
            await self.set_name()
            return

        if message.content == "!dcmc shush":
            self.shushed = True
            return

        if message.content == "!dcmc unshush":
            self.shushed = False
            return

        p_factors = [
            self.shushed,
            "dcmc" in message.content,
            message.channel.name == "do-converse-me-channel",
        ]
        print("[shushed, contains dcmc, is dcmc channel]:", p_factors)

        match p_factors:
            case [False, True, True]:
                p = 1
            case [False, True, False]:
                p = 0.7
            case [False, False, True]:
                p = 0.4
            case [False, False, False]:
                p = 0
            case [True, _, _]:
                p = 0

        print("p:", p)

        if random.random() < p:
            async with message.channel.typing():
                completion = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=self.prompt(message.channel),
                    max_tokens=256,
                    temperature=1,
                    stop=["\n"],
                    frequency_penalty=0.5,
                    presence_penalty=0.5,
                )
                await asyncio.sleep(len(completion.choices[0].text) / 10)
                await message.channel.send(completion.choices[0].text)

                print(
                    f"posted - {completion.choices[0].text[:10]}... {self.adj1} {self.adj2}"
                )

        if random.random() < 0.02:
            self.adj1 = generate_adjective()
        if random.random() < 0.1:
            self.adj2 = generate_adjective()

        if random.random() < 0.05:
            self.shushed = False


intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(environ["DISCORD_TOKEN"])
