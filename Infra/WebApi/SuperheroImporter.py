class SuperheroImporter:

    URL_TEMPLATE = "https://superheroapi.com/api/{token}/{hero_id}/powerstats"
    STATS = ("strength", "durability", "intelligence", "combat", "speed")

    @classmethod
    def build_url(cls, token: str, hero_id: str) -> str:
        return cls.URL_TEMPLATE.format(token=token, hero_id=hero_id)

    @classmethod
    def to_save_data(cls, answer) -> dict:
        if not isinstance(answer, dict) or answer.get("response") != "success":
            reason = answer.get("error", "unexpected response") if isinstance(answer, dict) else "unexpected response"
            raise ValueError(reason)
        try:
            stat = {k: int(answer[k]) for k in cls.STATS}
            name = answer["name"]
        except KeyError as e:
            raise ValueError(f"response is missing {e}") from e
        except (TypeError, ValueError) as e:
            raise ValueError(f"response has a non numeric stat: {e}") from e

        max_hp = stat["intelligence"] + stat["combat"] + stat["speed"]
        return {
            "characters": [{
                "name": name,
                "id": 1,
                "max_hp": max_hp,
                "hp": max_hp,
                "base_armor": stat["durability"],
                "base_attack_power": stat["strength"],
                "isalive": True,
                "inventory": [],
                "abilities": [],
            }],
            "items": [],
            "abilities": [],
        }
