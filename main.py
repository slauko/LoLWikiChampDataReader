import aiohttp
import asyncio
from bs4 import BeautifulSoup
from slpp import slpp as lua

async def get_urls(session):
    allnames = []
    async with session.get("https://leagueoflegends.fandom.com/wiki/List_of_champions") as r:
        text = await r.text()
        soup = BeautifulSoup(text, "html.parser") 
        tables = soup.find_all("table")
        spans = tables[1].find_all("span", class_="inline-image")
        for index in range(2, len(spans)):
            raw_name = spans[index]["data-champion"]
            filter_name = "".join(char for char in raw_name if char.isalnum())
            if filter_name == "NunuWillump":
                filter_name = "Nunu"
            if filter_name == "Wukong":
                filter_name = "MonkeyKing"   
            allnames.append(filter_name) 

    urls = {}
    for name in allnames:
        urls[name] = "https://raw.communitydragon.org/latest/game/data/characters/"+name.lower()+"/"+name.lower()+".bin.json"

    return urls

async def get_json_from_page(session, url):
    async with session.get(url) as r:
        return await r.json()


async def get_spell_data(session, urls):
    tasks = []

    raw_spells = {}
    raw_missiles = {}
    raw_wrappers = {}
    raw_anythingelse = {}

    for url in urls.values():
        tasks.append(asyncio.create_task(get_json_from_page(session, url)))

    result = await asyncio.gather(*tasks)
    for champ_data in result:
        for champ_script in champ_data.values():
            try:
                if "mSpell" and "mScriptName" in champ_script: #champ_script["mScriptName"].find("Attack") == -1 and champ_script["mScriptName"].find("Passive") == -1 and champ_script["mSpell"]["__type"] == "SpellDataResource"
                    current_name = champ_script["mScriptName"]
                    current_spell = champ_script["mSpell"]
                    if current_name.find("Wrapper") >= 0:
                        raw_wrappers[current_name] = current_spell
                    else:
                        if current_name.find("Attack") == -1 and current_name.find("Passive") == -1 and current_name.find("VFX") == -1:
                            if len(current_spell) > 10:
                                if "mMissileSpec" in current_spell:
                                    raw_missiles[current_name] = current_spell
                                else:
                                    raw_spells[current_name] = current_spell
                            else:
                                raw_anythingelse[current_name] = current_spell

            except:
                pass    
    
    spelldata = {}
    for name, spell in raw_spells.items():
        spelldata[name] = {}
        if "castRange" in spell:
            spelldata[name]["Range"] = spell["castRange"][0]
        if "castRangeDisplayOverride" in spell:
            spelldata[name]["Range"] = spell["castRangeDisplayOverride"][0]
               
        if "mClientData" in spell:
            clientdata = spell["mClientData"]
            if "mTargeterDefinitions" in clientdata:
                targeter = clientdata["mTargeterDefinitions"]
                rangedata = targeter[len(targeter)-1]
                if "overrideBaseRange" in rangedata:
                    baserange = rangedata["overrideBaseRange"]
                    if "mPerLevelValues" in baserange:
                        spelldata[name]["Range"] = baserange["mPerLevelValues"][0]
                if "coneRange" in rangedata:
                    spelldata[name]["Range"] = rangedata["coneRange"]

        if "mCastTime" in spell:
            spelldata[name]["CastTime"] = spell["mCastTime"]
        else:
            spelldata[name]["CastTime"] = 0.5

        if "mMissileSpeed" in spell:
            spelldata[name]["MissileSpeed"] = spell["mMissileSpeed"]
        else:
            spelldata[name]["MissileSpeed"] = float("inf")
        
        spelldata[name]["Width"] = 0.00
        spelldata[name]["Collision"] = 0

    for name, missile in raw_missiles.items():
        if "mAlternateName" in missile:
            altName = missile["mAlternateName"]
            if altName in spelldata:
                if "mCastTime" in missile and spelldata[altName]["CastTime"] == 0.00:
                    spelldata[altName]["CastTime"] = missile["mCastTime"]
                if "mMissileSpec" in missile:
                    spec = missile["mMissileSpec"]
                    if "mMissileWidth" in spec:
                            spelldata[altName]["Width"] = spec["mMissileWidth"]
                    if "movementComponent" in spec:
                        component = spec["movementComponent"]
                        if "mSpeed" in component:
                            spelldata[altName]["MissileSpeed"] = component["mSpeed"]
                        if "mMaxSpeed" in component:
                            spelldata[altName]["MissileSpeed"] = component["mMaxSpeed"]
                if "bHasHitBone" in missile:
                    spelldata[name]["Collision"] = 1

                    
    for name, data in spelldata.items():
        for missilename, missile in raw_missiles.items():
            if missilename.find(name) >= 0:
                if "mCastTime" in missile and data["CastTime"] == 0.00:
                    data["CastTime"] = missile["mCastTime"]
                if "mMissileSpec" in missile:
                    spec = missile["mMissileSpec"]
                    if "mMissileWidth" in spec:
                            data["Width"] = spec["mMissileWidth"]
                    if "movementComponent" in spec:
                        component = spec["movementComponent"]
                        if "mSpeed" in component:
                            data["MissileSpeed"] = component["mSpeed"]
                        if "mMaxSpeed" in component:
                            data["MissileSpeed"] = component["mMaxSpeed"]
                if "bHasHitBone" in missile:
                    data["Collision"] = 1
        for wrappername, wrapper in raw_wrappers.items():
            if wrappername.find(name) >= 0:
                if "castRange" in wrapper:
                    data["Range"] = wrapper["castRange"][0]
                if "castRangeDisplayOverride" in wrapper:
                    data["Range"] = wrapper["castRangeDisplayOverride"][0]
                if "mCastTime" in wrapper:
                    data["CastTime"] = wrapper["mCastTime"]
                if "mLineWidth" in wrapper:
                    data["Width"] = wrapper["mLineWidth"]
                if "bHasHitBone" in wrapper:
                    data["Collision"] = 1


    #spelldata["missiles"] = raw_missiles
    return spelldata
    
async def main():
    async with aiohttp.ClientSession() as session:
        urls = await get_urls(session)
        spelldata = await get_spell_data(session, urls)
        return spelldata

result = asyncio.run(main())


#write into lua file
luatabledata = lua.encode(result)
with open('SpellData.lua', 'w') as f:
    f.write(luatabledata)

    