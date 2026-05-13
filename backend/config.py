"""
Configuration for all 18 classification dimensions.
Prompts extracted verbatim from the rlang/ reference implementation.
"""

import json
import os

RLANG_DIR = "/home/control/rlang"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Input batch files (sentences_part_1.json … sentences_part_10.json)
BATCHES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# ── Central Vertex AI configuration ──────────────────────────────────────────
# Change these to switch the GCP project, model, or region for all dimensions.
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION   = "global"
# ─────────────────────────────────────────────────────────────────────────────


def input_path(batch: int) -> str:
    return os.path.join(RLANG_DIR, f"sentences_part_{batch}.json")


def output_path(dimension: str, batch: int) -> str:
    return os.path.join(DATA_DIR, f"output_{dimension}_{batch}.json")


def refine_input_path(dimension: str, batch: int) -> str:
    """Input file for refine dimensions — stored in data/ alongside outputs."""
    return os.path.join(DATA_DIR, f"input_{dimension}_{batch}.json")


_DEFAULT_DIMENSIONS = {
    "childcare": {
        "label": "Childcare & Parental Leave",
        "model": "gemini-3-flash-preview",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Variable: 201_child (Childcare and Parental Leave)

Definition:
Party's position on whether childcare and parental leave are framed as public responsibilities supported by the state or as private matters of the family.

In some cases, proposals are not evidently liberal or conservative. Support for parental leave, for instance, can be intended to support equality and choice but can also be aimed at strengthening the traditional family. The Austrian introduction of Kinderbetreuungsgeld in 2002, for instance, was a generous childcare allowance that was devised as family support rather than with a modernizing intention, and should therefore be assessed as conservative

Another example of an unclear proposal is support for large families. Such support need not always have the intention of strengthening the family. When the arguments concern redistributive effects, for instance, support will be assessed as neutral

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
The party frames childcare and parental leave as private or family responsibilities, with limited or no state involvement. This includes positions that stress parental choice, family autonomy, or traditional caregiving arrangements, and that often oppose or restrict public childcare provision or extensive parental leave policies. This also includes policies supporting family based care work, like wages for motherhood.

Code 0 (Neutral):
Child care or parental leave are described without judgement or neither the family nor state level is clearly made responsible.

Code -1 (Liberal):
The party supports publicly provided or publicly funded childcare and/or parental leave as a social right. It includes positions that emphasize state responsibility, public services, or collective solutions to childcare.

Code 99 (No Relevance):
Care not specifically on children or a completely different topic is mentioned.

### Few-Shot Examples

Input: {"ID": 2324, "QuasiSentence": "For example, government subsidies and tax breaks for daycare discriminate against the traditional family."}
Output: {"ID": 2324, "QuasiSentence": "For example, government subsidies and tax breaks for daycare discriminate against the traditional family.", "Code": 1}

Input: {"ID": 1764, "QuasiSentence": "Until the introduction of family taxation, the family allowance will be converted into a tax credit from the 3rd child.)."}
Output: {"ID": 1764, "QuasiSentence": "Until the introduction of family taxation, the family allowance will be converted into a tax credit from the 3rd child.).", "Code": 1}

Input: {"ID": 1984, "QuasiSentence": "Raising wages for women on optional maternity leave"}
Output: {"ID": 1984, "QuasiSentence": "Raising wages for women on optional maternity leave", "Code": 1}

Input: {"ID": 1191, "QuasiSentence": "The SVP focuses on personal responsibility in the family, in childcare"}
Output: {"ID": 1191, "QuasiSentence": "The SVP focuses on personal responsibility in the family, in childcare", "Code": 1}

Input: {"ID": 32371, "QuasiSentence": "Child support, an active family policy and the right to quality child care are used to give our little ones every opportunity for a successful life."}
Output: {"ID": 32371, "QuasiSentence": "Child support, an active family policy and the right to quality child care are used to give our little ones every opportunity for a successful life.", "Code": 0}

Input: {"ID": 1051, "QuasiSentence": "Child-rich families do not have to make do with child support alone."}
Output: {"ID": 1051, "QuasiSentence": "Child-rich families do not have to make do with child support alone.", "Code": 0}

Input: {"ID": 1035, "QuasiSentence": "The Finns believe that municipalities should be given additional resources to prevent serious problems in families on a trial basis and see whether this reduces the need to place children outside their homes."}
Output: {"ID": 1035, "QuasiSentence": "The Finns believe that municipalities should be given additional resources to prevent serious problems in families on a trial basis and see whether this reduces the need to place children outside their homes.", "Code": -1}

Input: {"ID": 4091, "QuasiSentence": "There are families with problems, and parents who from time to time are unable to take their responsibilities. Of course, society has a responsibility to intervene when children are being harmed."}
Output: {"ID": 4091, "QuasiSentence": "There are families with problems, and parents who from time to time are unable to take their responsibilities. Of course, society has a responsibility to intervene when children are being harmed.", "Code": -1}

Input: {"ID": 2577, "QuasiSentence": "To promote informed family planning, we are launching public health programmes on starting a family, similar to those on smoking, with a special focus on the dangers of delaying the birth of the first child, and we"}
Output: {"ID": 2577, "QuasiSentence": "To promote informed family planning, we are launching public health programmes on starting a family, similar to those on smoking, with a special focus on the dangers of delaying the birth of the first child, and we", "Code": 99}

Input: {"ID": 48877, "QuasiSentence": "It may be better to provide care in the familiar home setting as much as possible, and to properly support the family in doing so."}
Output: {"ID": 48877, "QuasiSentence": "It may be better to provide care in the familiar home setting as much as possible, and to properly support the family in doing so.", "Code": 99}

Input: {"ID": 48604, "QuasiSentence": "women returning to the labor market after maternity leave"}
Output: {"ID": 48604, "QuasiSentence": "women returning to the labor market after maternity leave", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "edu": {
        "label": "Girls' Education",
        "model": "gemini-2.5-flash",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Instructions
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Definition:
tatements towards education for girls. This includes positions on gender-specific education, addressing gender stereotypes in education, and policies that restrict or expand girls' educational opportunities.
Coding Scheme:

- Code 1 (Conservative): The party advocates for measures that would restrict girls' education or promote gender-specific stereotypes that limit educational opportunities.

- Code 0 (Neutral): Education for girls is described without judgment or without advocating expansion or restriction.

- Code -1 (Liberal): The party advocates for measures that expand, protect, or strengthen girls' educational opportunities, or promote awareness of gender equality in education.

- Code 99 (No Relevance): Statements not specifically relating to girls' education.

### Few-Shot Examples

Input: {"ID": 430, "QuasiSentence": "An end to tax-funded support for gender education."}
Output: {"ID": 430, "QuasiSentence": "An end to tax-funded support for gender education.", "Code": 1}

Input: {"ID": 443, "QuasiSentence": "Repeal of all laws that from the so-called \"gender perspective\" generate inequality and social discord, facilitate the embezzlement of public money, indoctrinate minors and impose a single way of thinking through severe administrative sanctions and subsidized media support."}
Output: {"ID": 443, "QuasiSentence": "Repeal of all laws that from the so-called \"gender perspective\" generate inequality and social discord, facilitate the embezzlement of public money, indoctrinate minors and impose a single way of thinking through severe administrative sanctions and subsidized media support.", "Code": 1}

Input: {"ID": 1326, "QuasiSentence": "In some countries, such as Sweden, little boys are forced to play with dolls, while young girls can handle toy soldiers."}
Output: {"ID": 1326, "QuasiSentence": "In some countries, such as Sweden, little boys are forced to play with dolls, while young girls can handle toy soldiers.", "Code": 1}

Input: {"ID": 2016, "QuasiSentence": "Promotion of women-specific training and continuing education programs that are."}
Output: {"ID": 2016, "QuasiSentence": "Promotion of women-specific training and continuing education programs that are.", "Code": -1}

Input: {"ID": 15775, "QuasiSentence": "that, in addition to guaranteeing a stable educational system based on equity, equality between women and men and inclusiveness,"}
Output: {"ID": 15775, "QuasiSentence": "that, in addition to guaranteeing a stable educational system based on equity, equality between women and men and inclusiveness,", "Code": -1}

Input: {"ID": 3878, "QuasiSentence": "To balance the presence of men and women in all sectors of society, we need to act at a very early stage, to make girls understand that they have the same opportunities as boys."}
Output: {"ID": 3878, "QuasiSentence": "To balance the presence of men and women in all sectors of society, we need to act at a very early stage, to make girls understand that they have the same opportunities as boys.", "Code": -1}

Input: {"ID": 11790, "QuasiSentence": "A system of community service (participation in local and neighbourhood communities, associations, libraries, education, culture, sport, non-profit organisations, economic assistance, etc.) is introduced for all able-bodied social beneficiaries."}
Output: {"ID": 11790, "QuasiSentence": "A system of community service (participation in local and neighbourhood communities, associations, libraries, education, culture, sport, non-profit organisations, economic assistance, etc.) is introduced for all able-bodied social beneficiaries.", "Code": 99}

Input: {"ID": 1248, "QuasiSentence": "However, it is opposed to any financial support for organizations that promote \"single-parent families\" as a normal, progressive or even desirable way of life."}
Output: {"ID": 1248, "QuasiSentence": "However, it is opposed to any financial support for organizations that promote \"single-parent families\" as a normal, progressive or even desirable way of life.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "equal": {
        "label": "Gender Equality",
        "model": "gemini-3-flash-preview",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Instructions
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Definition:
Statements where the party positions itself on the equal treatment of genders.
This includes equal rights in general, visibility, anti-discrimination, gender-based laws, and broader equality between men and women.

- Code 1 (Conservative): The party advocates for measures that would restrict equal rights between genders or repeal gender equality legislation.
- Code 0 (Neutral): Equal rights between genders are described without judgment or without advocating expansion or restriction.
- Code -1 (Liberal): The party advocates for measures that expand, protect, or strengthen equal rights between genders.
- Code 99 (No Relevance): Statements not specifically relating to equal rights between genders.

### Few-Shot Examples
Input: {"ID": 1248, "QuasiSentence": "However, it is opposed to any financial support for organizations that promote \"single-parent families\" as a normal, progressive or even desirable way of life."}
Output: {"ID": 1248, "QuasiSentence": "However, it is opposed to any financial support for organizations that promote \"single-parent families\" as a normal, progressive or even desirable way of life.", "Code": 1}

Input: {"ID": 345, "QuasiSentence": "Repeal of the law on gender violence and of all regulations that discriminate one sex from the other."}
Output: {"ID": 345, "QuasiSentence": "Repeal of the law on gender violence and of all regulations that discriminate one sex from the other.", "Code": 1}

Input: {"ID": 443, "QuasiSentence": "70.Repeal of all laws that from the so-called \"gender perspective\" generate inequality and social discord, facilitate the embezzlement of public money, indoctrinate minors and impose a single way of thinking through severe administrative sanctions and subsidized media support"}
Output: {"ID": 443, "QuasiSentence": "70.Repeal of all laws that from the so-called \"gender perspective\" generate inequality and social discord, facilitate the embezzlement of public money, indoctrinate minors and impose a single way of thinking through severe administrative sanctions and subsidized media support", "Code": 1}

Input: {"ID": 43854, "QuasiSentence": "The EU has always been a major driver of gender equality over the past 30 years."}
Output: {"ID": 43854, "QuasiSentence": "The EU has always been a major driver of gender equality over the past 30 years.", "Code": 0}

Input: {"ID": 38761, "QuasiSentence": "The career account gives men and women the keys to plan their own careers and build their retirement rights."}
Output: {"ID": 38761, "QuasiSentence": "The career account gives men and women the keys to plan their own careers and build their retirement rights.", "Code": 0}

Input: {"ID": 402, "QuasiSentence": "Protecting women from social exclusion, violence and sexual exploitation is an obligation of any state that wants to be called socially just."}
Output: {"ID": 402, "QuasiSentence": "Protecting women from social exclusion, violence and sexual exploitation is an obligation of any state that wants to be called socially just.", "Code": -1}

Input: {"ID": 53313, "QuasiSentence": "Enterprises that do not use gender-neutral job classifications or those that discriminate in the granting of additional benefits or training cannot receive support measures."}
Output: {"ID": 53313, "QuasiSentence": "Enterprises that do not use gender-neutral job classifications or those that discriminate in the granting of additional benefits or training cannot receive support measures.", "Code": -1}

Input: {"ID": 48508, "QuasiSentence": "designing all public policies with a gender perspective"}
Output: {"ID": 48508, "QuasiSentence": "designing all public policies with a gender perspective", "Code": -1}

Input: {"ID": 317, "QuasiSentence": "No one may be discriminated against or given preferential treatment because of his or her gender."}
Output: {"ID": 317, "QuasiSentence": "No one may be discriminated against or given preferential treatment because of his or her gender.", "Code": -1}

Input: {"ID": 43562, "QuasiSentence": "4 We will continue our efforts to make women's competitive sports more visible and promote them, consolidating and improving the achievements made with respect to women in the field of sports"}
Output: {"ID": 43562, "QuasiSentence": "4 We will continue our efforts to make women's competitive sports more visible and promote them, consolidating and improving the achievements made with respect to women in the field of sports", "Code": -1}

Input: {"ID": 43882, "QuasiSentence": "We say this as a matter of principle: immigrants are, first and foremost, people, equal to all others in their dignity"}
Output: {"ID": 43882, "QuasiSentence": "We say this as a matter of principle: immigrants are, first and foremost, people, equal to all others in their dignity", "Code": 99}

Input: {"ID": 54249, "QuasiSentence": "Women who are willing to play a role in public life should be supported and helped to enter Parliament as individual MPs on party lists"}
Output: {"ID": 54249, "QuasiSentence": "Women who are willing to play a role in public life should be supported and helped to enter Parliament as individual MPs on party lists", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "famcare": {
        "label": "Family Care",
        "model": "gemini-2.5-flash",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
The party's position on whether care for family members is framed as a public responsibility supported by the state or as a private matter of the family.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
The party frames care of family members as private or family responsibility, with limited or no state involvement. This includes positions that stress family autonomy or traditional caregiving arrangements, and that often oppose or restrict public care provision.

Code 0 (Neutral):
Family member care is described without judgment.

Code -1 (Liberal):
The party supports publicly provided or publicly funded family member care as a social right. It includes positions that emphasize state responsibility, public services, or collective solutions to family member care. Solely having the care of family members by one person is seen as a problem. The party emphasises choice in the matter.

Code 99 (No Relevance):
Care not specifically on the family like only on children or a completely different topic is mentioned.

### Few-Shot Examples

Input: {"ID": 1704, "QuasiSentence": "Strong and warm families in which people take responsibility for each other and find love and mutual support are the foundation of our society."}
Output: {"ID": 1704, "QuasiSentence": "Strong and warm families in which people take responsibility for each other and find love and mutual support are the foundation of our society.", "Code": 1}

Input: {"ID": 48877, "QuasiSentence": "It may be better to provide care in the familiar home setting as much as possible, and to properly support the family in doing so."}
Output: {"ID": 48877, "QuasiSentence": "It may be better to provide care in the familiar home setting as much as possible, and to properly support the family in doing so.", "Code": 1}

Input: {"ID": 49459, "QuasiSentence": "By enabling family members to receive high-quality training, we can help our senior citizens to remain in their own homes for as long as possible, while guaranteeing a certain degree of autonomy (see proposition 221);"}
Output: {"ID": 49459, "QuasiSentence": "By enabling family members to receive high-quality training, we can help our senior citizens to remain in their own homes for as long as possible, while guaranteeing a certain degree of autonomy (see proposition 221);", "Code": 1}

Input: {"ID": 2559, "QuasiSentence": "Women also play a greater role in caring for older family members, so the"}
Output: {"ID": 2559, "QuasiSentence": "Women also play a greater role in caring for older family members, so the", "Code": 0}

Input: {"ID": 31066, "QuasiSentence": "Relieving the burden on family caregivers"}
Output: {"ID": 31066, "QuasiSentence": "Relieving the burden on family caregivers", "Code": 0}

Input: {"ID": 32763, "QuasiSentence": "people caring for dependent family members."}
Output: {"ID": 32763, "QuasiSentence": "people caring for dependent family members.", "Code": 0}

Input: {"ID": 2688, "QuasiSentence": "With an increase in the number of divorces, there are also more and more single people who have to take care of the family."}
Output: {"ID": 2688, "QuasiSentence": "With an increase in the number of divorces, there are also more and more single people who have to take care of the family.", "Code": -1}

Input: {"ID": 27834, "QuasiSentence": "That's why we want to step up material aid and assistance to families."}
Output: {"ID": 27834, "QuasiSentence": "That's why we want to step up material aid and assistance to families.", "Code": -1}

Input: {"ID": 29504, "QuasiSentence": "The family caregiver also has their limits and carrying capacity."}
Output: {"ID": 29504, "QuasiSentence": "The family caregiver also has their limits and carrying capacity.", "Code": -1}

Input: {"ID": 37561, "QuasiSentence": "Family caregivers should also always be able to turn to their municipality for support."}
Output: {"ID": 37561, "QuasiSentence": "Family caregivers should also always be able to turn to their municipality for support.", "Code": -1}

Input: {"ID": 48604, "QuasiSentence": "women returning to the labor market after maternity leave"}
Output: {"ID": 48604, "QuasiSentence": "women returning to the labor market after maternity leave", "Code": 99}

Input: {"ID": 2324, "QuasiSentence": "For example, government subsidies and tax breaks for daycare discriminate against the traditional family."}
Output: {"ID": 2324, "QuasiSentence": "For example, government subsidies and tax breaks for daycare discriminate against the traditional family.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "famplan": {
        "label": "Family Planning",
        "model": "gemini-2.5-flash",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
This code captures positions regarding reproductive autonomy and family planning, specifically whether individuals (especially women) are granted freedom to decide on the number and timing of children or whether family planning is restricted or socially/normatively constrained. It focuses on personal or familial autonomy, without reference to societal, national, or political objectives.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
Party statements that limit or constrain individual/couple autonomy in family planning, e.g., through social norms, laws, or pressure within the family.

Code 0 (Neutral):
Family planning is mentioned without a clear judgment.

Code -1 (Liberal):
The party emphasises an individual's or a couple's autonomy in reproductive decisions. It includes positions supporting access to contraception, reproductive rights, and voluntary decision-making about family size.

Code 99 (No Relevance):
Family planning is not mentioned or a different topic is mentioned.

### Few-Shot Examples

Input: {"ID": 644, "QuasiSentence": "BBB wants to maintain the mandatory five-day reflection period on abortion."}
Output: {"ID": 644, "QuasiSentence": "BBB wants to maintain the mandatory five-day reflection period on abortion.", "Code": 1}

Input: {"ID": 336, "QuasiSentence": "56.To suppress in the public health system surgical interventions unrelated to health (sex change, abortion...)"}
Output: {"ID": 336, "QuasiSentence": "56.To suppress in the public health system surgical interventions unrelated to health (sex change, abortion...)", "Code": 1}

Input: {"ID": 1103, "QuasiSentence": "Nor does the provision of fertility treatment to single women or couples of women represent any real solution to this issue, but is instead a selfish measure which violates the rights of the unborn child and which the True Finns believe should not be supported by social funding or allowed at all."}
Output: {"ID": 1103, "QuasiSentence": "Nor does the provision of fertility treatment to single women or couples of women represent any real solution to this issue, but is instead a selfish measure which violates the rights of the unborn child and which the True Finns believe should not be supported by social funding or allowed at all.", "Code": 1}

Input: {"ID": 999, "QuasiSentence": "We do not give same-sex couples the right to adopt."}
Output: {"ID": 999, "QuasiSentence": "We do not give same-sex couples the right to adopt.", "Code": 1}

Input: {"ID": 2576, "QuasiSentence": "To promote informed family planning, we are launching public health programmes on starting a family, similar to those on smoking, with a special focus on the dangers of delaying the birth of the first child, and we"}
Output: {"ID": 2576, "QuasiSentence": "To promote informed family planning, we are launching public health programmes on starting a family, similar to those on smoking, with a special focus on the dangers of delaying the birth of the first child, and we", "Code": 0}

Input: {"ID": 7546, "QuasiSentence": "- We will guarantee assisted reproduction treatments to all women, regardless of their sexual orientation and marital status, once this right has been reestablished in the portfolio of common services of the National Health System."}
Output: {"ID": 7546, "QuasiSentence": "- We will guarantee assisted reproduction treatments to all women, regardless of their sexual orientation and marital status, once this right has been reestablished in the portfolio of common services of the National Health System.", "Code": -1}

Input: {"ID": 13224, "QuasiSentence": "We advocate for their right to self-determination and family planning."}
Output: {"ID": 13224, "QuasiSentence": "We advocate for their right to self-determination and family planning.", "Code": -1}

Input: {"ID": 1152, "QuasiSentence": "Adoption laws and foster parenting should also be relaxed."}
Output: {"ID": 1152, "QuasiSentence": "Adoption laws and foster parenting should also be relaxed.", "Code": -1}

Input: {"ID": 27834, "QuasiSentence": "That is why we want to step up material aid and assistance to families."}
Output: {"ID": 27834, "QuasiSentence": "That is why we want to step up material aid and assistance to families.", "Code": 99}

Input: {"ID": 34720, "QuasiSentence": "Guarantee and strengthen support for the most vulnerable families, with an adequate treatment of the new types of families"}
Output: {"ID": 34720, "QuasiSentence": "Guarantee and strengthen support for the most vulnerable families, with an adequate treatment of the new types of families", "Code": 99}

Input: {"ID": 1764, "QuasiSentence": "Until the introduction of family taxation, the family allowance will be converted into a tax credit from the 3rd child.)."}
Output: {"ID": 1764, "QuasiSentence": "Until the introduction of family taxation, the family allowance will be converted into a tax credit from the 3rd child.).", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "femim": {
        "label": "Female Immigrant Rights (General)",
        "model": "gemini-3-flash-preview",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
Statements about female immigrants' rights in general. This includes general support or restriction of female immigrants' rights without referring to specific policy instruments such as bans, family reunification rules, or protection from specific practices (these belong to Code 11).

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>" }

Coding Scheme:

Code 1 (Conservative):
The party positions on the restriction of female immigrants' rights in general.

Code 0 (Neutral):
Female immigrants' rights are mentioned descriptively without clear support or restriction.

Code -1 (Liberal):
The party positions on the support of female immigrants' rights in general.

Code 99 (No Relevance):
Specific policies (e.g., forced marriage, FGM, headscarf bans, family reunification), general immigration issues, or entirely different topics.

### Few-Shot Examples

Input: {"ID": 391, "QuasiSentence": "The sheer weight of numbers, combined with rising birth rates (particularly to immigrant mothers) and an ageing population, is pushing public services to breaking point."}
Output: {"ID": 391, "QuasiSentence": "The sheer weight of numbers, combined with rising birth rates (particularly to immigrant mothers) and an ageing population, is pushing public services to breaking point.", "Code": 1}

Input: {"ID": 36378, "QuasiSentence": "Female migrants in particular often live in Germany for years without being able to establish contact with German citizens."}
Output: {"ID": 36378, "QuasiSentence": "Female migrants in particular often live in Germany for years without being able to establish contact with German citizens.", "Code": 0}

Input: {"ID": 67, "QuasiSentence": "It is in some immigrant communities that gender equality has fallen shortest."}
Output: {"ID": 67, "QuasiSentence": "It is in some immigrant communities that gender equality has fallen shortest.", "Code": -1}

Input: {"ID": 14887, "QuasiSentence": "Female immigrants and first-generation Norwegians should have the same opportunities and rights as other women."}
Output: {"ID": 14887, "QuasiSentence": "Female immigrants and first-generation Norwegians should have the same opportunities and rights as other women.", "Code": -1}

Input: {"ID": 238, "QuasiSentence": "No Islamic gender apartheid; not at civic integration courses, not at theaters, not at libraries, not at swimming pools or anywhere else"}
Output: {"ID": 238, "QuasiSentence": "No Islamic gender apartheid; not at civic integration courses, not at theaters, not at libraries, not at swimming pools or anywhere else", "Code": -1}

Input: {"ID": 1101, "QuasiSentence": "In municipalities where the immigrant population has become concentrated in certain areas, the True Finns support the idea of maximum quotas per school for pupils with an immigrant background, as the concentration of MAM pupils in only certain schools undermines their integration into Finnish society."}
Output: {"ID": 1101, "QuasiSentence": "In municipalities where the immigrant population has become concentrated in certain areas, the True Finns support the idea of maximum quotas per school for pupils with an immigrant background, as the concentration of MAM pupils in only certain schools undermines their integration into Finnish society.", "Code": 99}

Input: {"ID": 21692, "QuasiSentence": "Forced marriages, honor killings, violence, pressure to wear a headscarf, re-education trips, bans on recreational activities."}
Output: {"ID": 21692, "QuasiSentence": "Forced marriages, honor killings, violence, pressure to wear a headscarf, re-education trips, bans on recreational activities.", "Code": 99}

Input: {"ID": 48877, "QuasiSentence": "It may be better to provide care in the familiar home setting as much as possible, and to properly support the family in doing so."}
Output: {"ID": 48877, "QuasiSentence": "It may be better to provide care in the familiar home setting as much as possible, and to properly support the family in doing so.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "femimspec": {
        "label": "Female Immigrant Rights (Specific)",
        "model": "gemini-2.5-flash",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Variable: 11_femimspec (Specific immigrant women's rights)

Definition:
Statements about specific rights of female immigrants. This includes positions on burkas, headscarves, family reunifications, immigrant family allowances, and protection from practices such as forced marriage, genital mutilation, honour killings, or rape. The code captures whether rights are restricted, supported, or neutrally mentioned.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
The party positions on the restriction of female immigrants' rights in general. This includes restrictions on burkas, headscarves, family reunifications or immigrant family allowances.

Code 0 (Neutral):
Specific female immigrants' rights are mentioned without judgment, or both restrictive and expansive measures are mentioned within the same sentence.

Code -1 (Liberal):
The party positions on the support of specific female immigrants' rights in general. This includes protection from forced marriages, rape, genital mutilation, honour killings or the easier access to family reunifications and immigrant family allowances.

Code 99 (No Relevance):
General positions on gender, women or immigration that do not include a specific policy regarding female immigrants' rights, or entirely different topics.

### Few-Shot Examples

Input: {"ID": 1610, "QuasiSentence": "The Act imposes a livelihood requirement on immigrants living in Finland who apply for family reunification."}
Output: {"ID": 1610, "QuasiSentence": "The Act imposes a livelihood requirement on immigrants living in Finland who apply for family reunification.", "Code": 1}

Input: {"ID": 846, "QuasiSentence": "- ban in government administrations, Community Education Schools, the military and the magistracy of the Islamic headscarf, which is not a strictly religious symbol but a political position on the inequality of men and women."}
Output: {"ID": 846, "QuasiSentence": "- ban in government administrations, Community Education Schools, the military and the magistracy of the Islamic headscarf, which is not a strictly religious symbol but a political position on the inequality of men and women.", "Code": 1}

Input: {"ID": 21692, "QuasiSentence": "Forced marriages, honor killings, violence, pressure to wear a headscarf, re-education trips, bans on recreational activities."}
Output: {"ID": 21692, "QuasiSentence": "Forced marriages, honor killings, violence, pressure to wear a headscarf, re-education trips, bans on recreational activities.", "Code": 0}

Input: {"ID": 27885, "QuasiSentence": "Compulsory education on rape, women's rights and norms must be given more space in the introduction program for newly arrived immigrants."}
Output: {"ID": 27885, "QuasiSentence": "Compulsory education on rape, women's rights and norms must be given more space in the introduction program for newly arrived immigrants.", "Code": -1}

Input: {"ID": 1925, "QuasiSentence": "or which conflict with British values and customs, including forced marriages, female genital mutilation and 'so-called' honour killings."}
Output: {"ID": 1925, "QuasiSentence": "or which conflict with British values and customs, including forced marriages, female genital mutilation and 'so-called' honour killings.", "Code": -1}

Input: {"ID": 52146, "QuasiSentence": "support organizations working to prevent female genital mutilation, forced marriages and honor crimes;"}
Output: {"ID": 52146, "QuasiSentence": "support organizations working to prevent female genital mutilation, forced marriages and honor crimes;", "Code": -1}

Input: {"ID": 37061, "QuasiSentence": "Promote family reunification as a way of consolidating the integration of migrants into Portuguese society;"}
Output: {"ID": 37061, "QuasiSentence": "Promote family reunification as a way of consolidating the integration of migrants into Portuguese society;", "Code": -1}

Input: {"ID": 14887, "QuasiSentence": "Female immigrants and first-generation Norwegians should have the same opportunities and rights as other women."}
Output: {"ID": 14887, "QuasiSentence": "Female immigrants and first-generation Norwegians should have the same opportunities and rights as other women.", "Code": 99}

Input: {"ID": 48877, "QuasiSentence": "It may be better to provide care in the familiar home setting as much as possible, and to properly support the family in doing so."}
Output: {"ID": 48877, "QuasiSentence": "It may be better to provide care in the familiar home setting as much as possible, and to properly support the family in doing so.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "labour": {
        "label": "Women's Labour Market",
        "model": "gemini-2.5-flash",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Instructions
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

- Code: 1 (Conservative): The party advocates for measures that would restrict opportunities for women in the labour market. These include incentives for the single-earner family model like emphasis on a motherhood pension.
- Code: 0 (Neutral): Womens opportunities in the labour market are described without judgment. Pension splitting is mentioned without a clear indication towards the single-earner or motherhood model.
- Code: -1 (Liberal): The party advocates for measures that would expand opportunities for women in the labour market. They see discrimination based on gender in the job market as a problem.
- Code: 99 (No Relevance): Sentences not specifically relating to the expansion or restriction of womens labor market opportunities.

### Few-Shot Examples
Input: {"ID": 92, "QuasiSentence": "Depending on the number of children, women should be entitled to a basic pension, which must be expanded to a maternity pension."}
Output: {"ID": 92, "QuasiSentence": "Depending on the number of children, women should be entitled to a basic pension, which must be expanded to a maternity pension.", "Code": 1}

Input: {"ID": 745, "QuasiSentence": "Instead of gender theories and quotas, implement real improvements in working conditions in female-dominated professions by, among other things, increasing the right to full-time work and abolishing part-time work"}
Output: {"ID": 745, "QuasiSentence": "Instead of gender theories and quotas, implement real improvements in working conditions in female-dominated professions by, among other things, increasing the right to full-time work and abolishing part-time work", "Code": 1}

Input: {"ID": 23040, "QuasiSentence": "The principle of pension splitting is introduced for men and women."}
Output: {"ID": 23040, "QuasiSentence": "The principle of pension splitting is introduced for men and women.", "Code": 0}

Input: {"ID": 47807, "QuasiSentence": "Women's work has become more widespread in younger cohorts"}
Output: {"ID": 47807, "QuasiSentence": "Women's work has become more widespread in younger cohorts", "Code": 0}

Input: {"ID": 16900, "QuasiSentence": "We want to step up efforts to broaden the range of career choices for women."}
Output: {"ID": 16900, "QuasiSentence": "We want to step up efforts to broaden the range of career choices for women.", "Code": -1}

Input: {"ID": 27812, "QuasiSentence": "better opportunities for women in management positions, for example by setting targets for increasing the proportion of women on supervisory boards."}
Output: {"ID": 27812, "QuasiSentence": "better opportunities for women in management positions, for example by setting targets for increasing the proportion of women on supervisory boards.", "Code": -1}

Input: {"ID": 402, "QuasiSentence": "We will promote productive projects for low-income families that will allow them to join the workforce and generate their own assets."}
Output: {"ID": 402, "QuasiSentence": "We will promote productive projects for low-income families that will allow them to join the workforce and generate their own assets.", "Code": 99}

Input: {"ID": 402, "QuasiSentence": "Protecting women from social exclusion, violence and sexual exploitation is an obligation of any state that wants to be called socially just."}
Output: {"ID": 402, "QuasiSentence": "Protecting women from social exclusion, violence and sexual exploitation is an obligation of any state that wants to be called socially just.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "lgbtq": {
        "label": "LGBTQ+ Rights",
        "model": "gemini-2.5-flash",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
Statements about LGBTQ+ rights in general. This includes party positions supporting or restricting rights such as same-sex marriage, adoption, transgender rights, civil status changes, fertility treatment for same-sex couples, or general equal rights for LGBTQ+ persons.

IMPORTANT:
- The statement must concern LGBTQ+ rights in general.
- If the statement refers specifically to immigrant LGBTQ+ persons, classify under Code 21 instead.
- If it refers only to women, families, or unrelated topics, classify as 99.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99).
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>" }

Coding Scheme:

Code 1 (Conservative):
The party positions on the restriction of LGBTQ+ rights in general.

Code 0 (Neutral):
LGBTQ+ rights are mentioned descriptively without clear support or restriction.

Code -1 (Liberal):
The party positions on the support of LGBTQ+ rights in general.

Code 99 (No Relevance):
Statements referring only to women, families, immigration without LGBTQ+ reference, or entirely different topics.

### Few-Shot Examples

Input: {"ID": 1103, "QuasiSentence": "Nor does the provision of fertility treatment to single women or couples of women represent any real solution to this issue, but is instead a selfish measure which violates the rights of the unborn child and which the True Finns believe should not be supported by social funding or allowed at all."}
Output: {"ID": 1103, "QuasiSentence": "Nor does the provision of fertility treatment to single women or couples of women represent any real solution to this issue, but is instead a selfish measure which violates the rights of the unborn child and which the True Finns believe should not be supported by social funding or allowed at all.", "Code": 1}

Input: {"ID": 55622, "QuasiSentence": "From marriage for same-sex couples to adoption for same-sex couples, from co-maternity to changes in civil status for transgender people, the PS has been a forerunner in every struggle."}
Output: {"ID": 55622, "QuasiSentence": "From marriage for same-sex couples to adoption for same-sex couples, from co-maternity to changes in civil status for transgender people, the PS has been a forerunner in every struggle.", "Code": -1}

Input: {"ID": 28129, "QuasiSentence": "Social Democrats have always fought for equal rights and opportunities for all; for women's right to vote, for gay rights, basic civil rights for all."}
Output: {"ID": 28129, "QuasiSentence": "Social Democrats have always fought for equal rights and opportunities for all; for women's right to vote, for gay rights, basic civil rights for all.", "Code": -1}

Input: {"ID": 14887, "QuasiSentence": "Female immigrants and first-generation Norwegians should have the same opportunities and rights as other women."}
Output: {"ID": 14887, "QuasiSentence": "Female immigrants and first-generation Norwegians should have the same opportunities and rights as other women.", "Code": 99}

Input: {"ID": 1326, "QuasiSentence": "In some countries, such as Sweden, little boys are forced to play with dolls, while young girls can handle toy soldiers."}
Output: {"ID": 1326, "QuasiSentence": "In some countries, such as Sweden, little boys are forced to play with dolls, while young girls can handle toy soldiers.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "lgbtqim": {
        "label": "LGBTQ+ Immigrant Rights",
        "model": "gemini-3-flash-preview",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
Statements about policies addressing immigrant LGBTQ+ persons. This includes policies to combat discrimination, provide protection, prioritize reception, or restrict rights of immigrant LGBTQ+ individuals. The statement must clearly relate to BOTH immigration and LGBTQ+ status.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>" }

Coding Scheme:

Code 1 (Conservative):
Party statements supporting policies that restrict immigrant LGBTQ+ persons.

Code 0 (Neutral):
Policies toward immigrant LGBTQ+ persons are mentioned descriptively without clear support or restriction.

Code -1 (Liberal):
Party statements supporting policies that protect, prioritize, or expand rights of immigrant LGBTQ+ persons.

Code 99 (No Relevance):
Statements referring only to LGBTQ+ issues in general, only immigration issues in general, only women, or entirely different topics.

### Few-Shot Examples

Input: {"ID": 9999, "QuasiSentence": "Rejecting migrants with transgender ideology"}
Output: {"ID": 9999, "QuasiSentence": "Rejecting migrants with transgender ideology", "Code": 1}

Input: {"ID": 17154, "QuasiSentence": "Prioritising women and LGBTQ people in the reception of quota refugees"}
Output: {"ID": 17154, "QuasiSentence": "Prioritising women and LGBTQ people in the reception of quota refugees", "Code": -1}

Input: {"ID": 24717, "QuasiSentence": "Introduce gender equality and LGBTQ rights as part of the compulsory social orientation for new arrivals"}
Output: {"ID": 24717, "QuasiSentence": "Introduce gender equality and LGBTQ rights as part of the compulsory social orientation for new arrivals", "Code": -1}

Input: {"ID": 35010, "QuasiSentence": "Furthermore, shelters should be provided for immigrant homosexuals who fall between the cracks."}
Output: {"ID": 35010, "QuasiSentence": "Furthermore, shelters should be provided for immigrant homosexuals who fall between the cracks.", "Code": -1}

Input: {"ID": 14887, "QuasiSentence": "Female immigrants and first-generation Norwegians should have the same opportunities and rights as other women."}
Output: {"ID": 14887, "QuasiSentence": "Female immigrants and first-generation Norwegians should have the same opportunities and rights as other women.", "Code": 99}

Input: {"ID": 55622, "QuasiSentence": "From marriage for same-sex couples to adoption for same-sex couples, from co-maternity to changes in civil status for transgender people, the PS has been a forerunner in every struggle."}
Output: {"ID": 55622, "QuasiSentence": "From marriage for same-sex couples to adoption for same-sex couples, from co-maternity to changes in civil status for transgender people, the PS has been a forerunner in every struggle.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "mix": {
        "label": "Mixed/Interethnic Marriages",
        "model": "gemini-2.5-flash",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
Statements about unions between individuals of different races, religions, cultures, or ethnicities. This targets cross-border, international, interfaith, and interethnic marriages.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
The party position describes mixed marriages negatively.

Code 0 (Neutral):
Mixed marriages are mentioned without judgment.

Code -1 (Liberal):
The party position describes mixed marriages positively.

Code 99 (No Relevance):
The statement does not refer to mixed marriages (cross-border, interfaith, interethnic, intercultural unions).

### Few-Shot Examples

Input: {"ID": 511, "QuasiSentence": "for the defense of the Polish family"}
Output: {"ID": 511, "QuasiSentence": "for the defense of the Polish family", "Code": 1}

Input: {"ID": 43327, "QuasiSentence": "This can often be particularly important for multicultural families."}
Output: {"ID": 43327, "QuasiSentence": "This can often be particularly important for multicultural families.", "Code": 0}

Input: {"ID": 40888, "QuasiSentence": "Spain is an increasingly diverse society, where people of different racial, ethnic or national origins, with different abilities, who express their sexuality and gender identity freely and consciously, who form family models different from the traditional one and who profess, or not, different faiths, live together."}
Output: {"ID": 40888, "QuasiSentence": "Spain is an increasingly diverse society, where people of different racial, ethnic or national origins, with different abilities, who express their sexuality and gender identity freely and consciously, who form family models different from the traditional one and who profess, or not, different faiths, live together.", "Code": -1}

Input: {"ID": 22153, "QuasiSentence": "Objective 3: IMPROVE THE LEGAL AND FINANCIAL POSITION OF CHILDREN IN INTERNATIONAL MARRIAGE AND SIMPLIFY PROCEDURES FOR SLOVENE PARENTS"}
Output: {"ID": 22153, "QuasiSentence": "Objective 3: IMPROVE THE LEGAL AND FINANCIAL POSITION OF CHILDREN IN INTERNATIONAL MARRIAGE AND SIMPLIFY PROCEDURES FOR SLOVENE PARENTS", "Code": -1}

Input: {"ID": 48463, "QuasiSentence": "Single-parent families are at high risk of poverty (53%)."}
Output: {"ID": 48463, "QuasiSentence": "Single-parent families are at high risk of poverty (53%).", "Code": 99}

Input: {"ID": 999, "QuasiSentence": "We do not give same-sex couples the right to adopt."}
Output: {"ID": 999, "QuasiSentence": "We do not give same-sex couples the right to adopt.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "nontradfam": {
        "label": "Non-Traditional Families",
        "model": "gemini-3-flash-preview",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
This code targets the parties concept of family and marriage. The code differentiates if the party emphasises an exclusive, certain ideal of family and marriage, while others are more inclusive.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
The party is against non-traditional family models or advocates for marriages & traditional family models. This also includes positions that would render same-sex arrangements of inferior status to the traditional family model.

Code 0 (Neutral):
(Non-)Traditional families are mentioned without judgment.

Code -1 (Liberal):
The party supports or normalizes non-traditional family models. This includes statements that render same sex agreements and traditional family models as being of equal status.

Code 99 (No Relevance):
The value of Traditional Families or non-traditional families is not mentioned or completely different topic is mentioned.

### Few-Shot Examples

Input: {"ID": 2433, "QuasiSentence": "For example, state subsidies and tax breaks for crèche care discriminate against the traditional family."}
Output: {"ID": 2433, "QuasiSentence": "For example, state subsidies and tax breaks for crèche care discriminate against the traditional family.", "Code": 1}

Input: {"ID": 999, "QuasiSentence": "We do not give same-sex couples the right to adopt."}
Output: {"ID": 999, "QuasiSentence": "We do not give same-sex couples the right to adopt.", "Code": 1}

Input: {"ID": 13862, "QuasiSentence": "The IRL believes that marriage is a union between a man and a woman."}
Output: {"ID": 13862, "QuasiSentence": "The IRL believes that marriage is a union between a man and a woman.", "Code": 1}

Input: {"ID": 2654, "QuasiSentence": "In addition to the traditional family and newly formed families, there are increasing numbers of single parents or singles without children."}
Output: {"ID": 2654, "QuasiSentence": "In addition to the traditional family and newly formed families, there are increasing numbers of single parents or singles without children.", "Code": 0}

Input: {"ID": 55622, "QuasiSentence": "From marriage for same-sex couples to adoption for same-sex couples, from co-maternity to changes in civil status for transgender people, the PS has been a forerunner in every struggle."}
Output: {"ID": 55622, "QuasiSentence": "From marriage for same-sex couples to adoption for same-sex couples, from co-maternity to changes in civil status for transgender people, the PS has been a forerunner in every struggle.", "Code": -1}

Input: {"ID": 34720, "QuasiSentence": "Guarantee and strengthen support for the most vulnerable families, with an adequate treatment of the new types of families"}
Output: {"ID": 34720, "QuasiSentence": "Guarantee and strengthen support for the most vulnerable families, with an adequate treatment of the new types of families", "Code": -1}

Input: {"ID": 48463, "QuasiSentence": "Single-parent families are at high risk of poverty (53%)."}
Output: {"ID": 48463, "QuasiSentence": "Single-parent families are at high risk of poverty (53%).", "Code": 99}

Input: {"ID": 27834, "QuasiSentence": "That is why we want to step up material aid and assistance to families."}
Output: {"ID": 27834, "QuasiSentence": "That is why we want to step up material aid and assistance to families.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "part": {
        "label": "Women's Political Participation",
        "model": "gemini-2.5-flash",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
Statements regarding women's participation in politics. The code distinguishes between positions that restrict or oppose targeted promotion of women in politics, neutral mentions, and positions that support expanding women's political participation.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
The party advocates for measures that would restrict women's participation in politics or sets skill and merit into the focus of political promotion.

Code 0 (Neutral):
Women's participation in politics is described without judgment.

Code -1 (Liberal):
The party advocates for measures that would expand women's participation in politics.

Code 99 (No Relevance):
The position is not on political participation or equality in politics or an entirely different topic is mentioned.

### Few-Shot Examples

Input: {"ID": 1689, "QuasiSentence": "c)Not allowing the implementation of gender ideologies or feminist perspectives in urban and territorial planning."}
Output: {"ID": 1689, "QuasiSentence": "c)Not allowing the implementation of gender ideologies or feminist perspectives in urban and territorial planning.", "Code": 1}

Input: {"ID": 99999, "QuasiSentence": "Public office should be awarded based on merit and qualifications, not gender."}
Output: {"ID": 99999, "QuasiSentence": "Public office should be awarded based on merit and qualifications, not gender.", "Code": 1}

Input: {"ID": 28894, "QuasiSentence": "Some provisions common to national electoral regulations (minimum voting age, gender parity, proportionality, etc.)."}
Output: {"ID": 28894, "QuasiSentence": "Some provisions common to national electoral regulations (minimum voting age, gender parity, proportionality, etc.).", "Code": 0}

Input: {"ID": 54249, "QuasiSentence": "Women who are willing to play a role in public life should be supported and helped to enter Parliament as individual MPs on party lists,"}
Output: {"ID": 54249, "QuasiSentence": "Women who are willing to play a role in public life should be supported and helped to enter Parliament as individual MPs on party lists,", "Code": -1}

Input: {"ID": 6294, "QuasiSentence": "Women must be given dignified representation in all elected assemblies and in leading national and local government offices."}
Output: {"ID": 6294, "QuasiSentence": "Women must be given dignified representation in all elected assemblies and in leading national and local government offices.", "Code": -1}

Input: {"ID": 15775, "QuasiSentence": "that, in addition to guaranteeing a stable educational system based on equity, equality between women and men and inclusiveness,"}
Output: {"ID": 15775, "QuasiSentence": "that, in addition to guaranteeing a stable educational system based on equity, equality between women and men and inclusiveness,", "Code": 99}

Input: {"ID": 402, "QuasiSentence": "Protecting women from social exclusion, violence and sexual exploitation is an obligation of any state that wants to be called socially just."}
Output: {"ID": 402, "QuasiSentence": "Protecting women from social exclusion, violence and sexual exploitation is an obligation of any state that wants to be called socially just.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "pronat": {
        "label": "Pro-Natalism",
        "model": "gemini-2.5-flash",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
Statements of the party on the macro-level, where the family is a tool of national or societal policy. They emphasise a large number of children as a public, societal, or national goal.

Instructions:
- Assign exactly one numeric code (1 or 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative / Pronatalist):
The party supports the idea of large families as the cornerstone of the nation. They suggest policies targeting larger families, often proposing financial support for them. This also includes financial support for women who chose not to abort.

Code 99 (No Relevance):
The statement does not frame large families or high birth rates as a societal or national goal.

### Few-Shot Examples

Input: {"ID": 2760, "QuasiSentence": "We will therefore introduce a monthly family allowance of PLN 500 for each second, third and subsequent children in the family."}
Output: {"ID": 2760, "QuasiSentence": "We will therefore introduce a monthly family allowance of PLN 500 for each second, third and subsequent children in the family.", "Code": 1}

Input: {"ID": 404, "QuasiSentence": "-Subsidising maternity and generously supporting families with three or more children."}
Output: {"ID": 404, "QuasiSentence": "-Subsidising maternity and generously supporting families with three or more children.", "Code": 1}

Input: {"ID": 7546, "QuasiSentence": "- We will guarantee assisted reproduction treatments to all women, regardless of their sexual orientation and marital status, once this right has been reestablished in the portfolio of common services of the National Health System."}
Output: {"ID": 7546, "QuasiSentence": "- We will guarantee assisted reproduction treatments to all women, regardless of their sexual orientation and marital status, once this right has been reestablished in the portfolio of common services of the National Health System.", "Code": 99}

Input: {"ID": 1984, "QuasiSentence": "Raising wages for women on optional maternity leave"}
Output: {"ID": 1984, "QuasiSentence": "Raising wages for women on optional maternity leave", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "quota": {
        "label": "Gender Quotas in Politics",
        "model": "gemini-3-flash-preview",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
Describes positions regarding gender quotas in politics. Such measures include, i.e., women's quota on party lists, a set number of seats going to women.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
The party is against a gender quota in politics.

Code 0 (Neutral):
Gender quota in politics is mentioned without judgment.

Code -1 (Liberal):
The party is for a gender quota in politics.

Code 99 (No Relevance):
The statement does not refer to gender quotas in politics.

### Few-Shot Examples

Input: {"ID": 607, "QuasiSentence": "1. that the public sector shall not apply any form of quotas based on race, religion, gender or ethnic origin,"}
Output: {"ID": 607, "QuasiSentence": "1. that the public sector shall not apply any form of quotas based on race, religion, gender or ethnic origin,", "Code": 1}

Input: {"ID": 8982, "QuasiSentence": "Gender equality without quotas"}
Output: {"ID": 8982, "QuasiSentence": "Gender equality without quotas", "Code": 1}

Input: {"ID": 28894, "QuasiSentence": "Some provisions common to national electoral regulations (minimum voting age, gender parity, proportionality, etc.)."}
Output: {"ID": 28894, "QuasiSentence": "Some provisions common to national electoral regulations (minimum voting age, gender parity, proportionality, etc.).", "Code": 0}

Input: {"ID": 10813, "QuasiSentence": "building mechanisms (political quotas, parity competitions for positions) through which women can more effectively take advantage of their equal social status."}
Output: {"ID": 10813, "QuasiSentence": "building mechanisms (political quotas, parity competitions for positions) through which women can more effectively take advantage of their equal social status.", "Code": -1}

Input: {"ID": 7712, "QuasiSentence": "We will propose the reform of the Electoral Law to guarantee a balanced presence on electoral lists - neither more than 60% nor less than 40% - of men or women in order to move towards parity democracy."}
Output: {"ID": 7712, "QuasiSentence": "We will propose the reform of the Electoral Law to guarantee a balanced presence on electoral lists - neither more than 60% nor less than 40% - of men or women in order to move towards parity democracy.", "Code": -1}

Input: {"ID": 12794, "QuasiSentence": "France is populated by a good half of women, a good quarter of young people, and a good fifth of French people of more or less foreign origin..."}
Output: {"ID": 12794, "QuasiSentence": "France is populated by a good half of women, a good quarter of young people, and a good fifth of French people of more or less foreign origin...", "Code": 99}

Input: {"ID": 27812, "QuasiSentence": "better opportunities for women in management positions, for example by setting targets for increasing the proportion of women on supervisory boards."}
Output: {"ID": 27812, "QuasiSentence": "better opportunities for women in management positions, for example by setting targets for increasing the proportion of women on supervisory boards.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "repfam": {
        "label": "Family vs. Individual Representation",
        "model": "gemini-3-flash-preview",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
Political statements that frame individuals or families as the primary subjects of representation, rights, and interests. The code distinguishes between positions that emphasize individual autonomy (e.g. women represented as independent persons) and positions that prioritize the family as a collective unit, often linking individuals—especially women—to their roles within the family. A tax reduction for families rather than an individually based reduction, intended to support the traditional one-breadwinner family, should be assessed as conservative. The code is used to assess whether gender relations are framed in an individualistic or family-centered manner.

Convention:
A tax reduction for families rather than an individually based reduction, intended to support the traditional one-breadwinner family, should be assessed as conservative. (Akkerman 2015, p.43)

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
The party describes family as the essential unit in society and the core pillar of interests. Individuals, especially women, are defined in the context of the family. The family is the receiver of rights and interests.

Code 0 (Neutral):
Representation of individuals/families is described without judgment.

Code -1 (Liberal):
The party describes individuals as having individual autonomy (e.g., women represented as independent persons). Women are defined as individuals or citizens rather than in their role within the family.

Code 99 (No Relevance):
The representational unit (individual vs. family) is not clear or a completely different topic is mentioned.

### Few-Shot Examples

Input: {"ID": 139, "QuasiSentence": "We regard the family, which is based on the permanent union of a man and a woman, as the basic structure of social life, in which particularly important human needs are satisfied, including the need for closeness to other people."}
Output: {"ID": 139, "QuasiSentence": "We regard the family, which is based on the permanent union of a man and a woman, as the basic structure of social life, in which particularly important human needs are satisfied, including the need for closeness to other people.", "Code": 1}

Input: {"ID": 1704, "QuasiSentence": "Strong and warm families in which people take responsibility for each other and find love and mutual support are the foundation of our society."}
Output: {"ID": 1704, "QuasiSentence": "Strong and warm families in which people take responsibility for each other and find love and mutual support are the foundation of our society.", "Code": 1}

Input: {"ID": 787, "QuasiSentence": "We are committed to moving away from individual taxation and toward family splitting as the most important measures to support our families."}
Output: {"ID": 787, "QuasiSentence": "We are committed to moving away from individual taxation and toward family splitting as the most important measures to support our families.", "Code": 1}

Input: {"ID": 13234, "QuasiSentence": "Define the boundaries of state, local government, community, family and individual responsibility, while ensuring that assistance is provided to those who really need it."}
Output: {"ID": 13234, "QuasiSentence": "Define the boundaries of state, local government, community, family and individual responsibility, while ensuring that assistance is provided to those who really need it.", "Code": 0}

Input: {"ID": 13067, "QuasiSentence": "Policies that broaden the real possibilities of individual choice, favor the sharing of responsibilities inside and outside the home, and reinforce the family as a voluntary and plural space for coexistence and affection."}
Output: {"ID": 13067, "QuasiSentence": "Policies that broaden the real possibilities of individual choice, favor the sharing of responsibilities inside and outside the home, and reinforce the family as a voluntary and plural space for coexistence and affection.", "Code": -1}

Input: {"ID": 49459, "QuasiSentence": "By enabling family members to receive high-quality training, we can help our senior citizens to remain in their own homes for as long as possible, while guaranteeing a certain degree of autonomy (see proposition 221);"}
Output: {"ID": 49459, "QuasiSentence": "By enabling family members to receive high-quality training, we can help our senior citizens to remain in their own homes for as long as possible, while guaranteeing a certain degree of autonomy (see proposition 221);", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "tradrole": {
        "label": "Traditional Gender Roles",
        "model": "gemini-3-flash-preview",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
The party positions itself on the division of traditionally gendered roles, especially paid work and unpaid care or household work, and whether these roles are framed as shared equally or as naturally or normatively gender-specific.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
The party supports or normalizes a gendered division of roles, typically assigning care and household responsibilities primarily to women and breadwinner roles primarily to men. It includes positions that portray such arrangements as natural, desirable, or socially necessary.

Code 0 (Neutral):
Gender roles are described without judgement.

Code -1 (Liberal):
The party supports an equal distribution of traditionally gendered roles between women and men, such as paid employment, childcare, and household labour. It includes positions that challenge traditional gender norms and promote egalitarian role arrangements.

Code 99 (No Relevance):
Care not specifically on traditional roles only or completely different topic is mentioned.

### Few-Shot Examples

Input: {"ID": 2532, "QuasiSentence": "The Progress Party wants to warn against a development where society takes on even more of the family's traditional tasks, thereby further weakening the role of the family in society."}
Output: {"ID": 2532, "QuasiSentence": "The Progress Party wants to warn against a development where society takes on even more of the family's traditional tasks, thereby further weakening the role of the family in society.", "Code": 1}

Input: {"ID": 2525, "QuasiSentence": "The family is an important carrier of tradition and culture, with the role of caregiver and educator as key characteristics."}
Output: {"ID": 2525, "QuasiSentence": "The family is an important carrier of tradition and culture, with the role of caregiver and educator as key characteristics.", "Code": 1}

Input: {"ID": 1217, "QuasiSentence": "A growing proportion of women are childless, so the most beautiful female vocation, motherhood (or fatherhood for men), is being enjoyed by a smaller and smaller proportion of people. The"}
Output: {"ID": 1217, "QuasiSentence": "A growing proportion of women are childless, so the most beautiful female vocation, motherhood (or fatherhood for men), is being enjoyed by a smaller and smaller proportion of people. The", "Code": 1}

Input: {"ID": 50731, "QuasiSentence": "Spanish families have transferred part of the caregiving responsibilities to grandparents (generally grandmothers)."}
Output: {"ID": 50731, "QuasiSentence": "Spanish families have transferred part of the caregiving responsibilities to grandparents (generally grandmothers).", "Code": 0}

Input: {"ID": 50403, "QuasiSentence": "Encouraging all sectors of society (culture, education, sport, media, science, research, etc.) to work to dismantle the traditional mentality about the role of women in society."}
Output: {"ID": 50403, "QuasiSentence": "Encouraging all sectors of society (culture, education, sport, media, science, research, etc.) to work to dismantle the traditional mentality about the role of women in society.", "Code": -1}

Input: {"ID": 14742, "QuasiSentence": "A Praxis analysis commissioned by the Ministry of Social Affairs in spring 2014 shows that a more successful reconciliation of work and family life and an increase in fathers participation in caring for young children is not possible without significant adjustments to the parental leave system."}
Output: {"ID": 14742, "QuasiSentence": "A Praxis analysis commissioned by the Ministry of Social Affairs in spring 2014 shows that a more successful reconciliation of work and family life and an increase in fathers participation in caring for young children is not possible without significant adjustments to the parental leave system.", "Code": -1}

Input: {"ID": 48604, "QuasiSentence": "women returning to the labor market after maternity leave"}
Output: {"ID": 48604, "QuasiSentence": "women returning to the labor market after maternity leave", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },

    "womorg": {
        "label": "Women's Organizations",
        "model": "gemini-2.5-flash",
        "prompt_template": """
Role
You are an expert political scientist specializing in manifesto coding. Your task is to classify Quasi-Sentences based on the provided codebook.

Definition:
Statements about women organising themselves for their interests. This can include women's organisations, NGOs, protests or social movements.

Instructions:
- Assign exactly one numeric code (1, 0, -1, 99)
- Output JSON in this format:
{ "ID": <ID>, "QuasiSentence": "<original>", "Code": "<assigned code>"}

Coding Scheme:

Code 1 (Conservative):
The party's position restricts women's organizations or their influence in politics.

Code 0 (Neutral):
Women's organizations or their influence in politics are described without judgement.

Code -1 (Liberal):
The party's position supports women's organizations or their influence in politics.

Code 99 (No Relevance):
No specific women/gender related organizational type is mentioned or a completely different topic is mentioned.

### Few-Shot Examples

Input: {"ID": 5599, "QuasiSentence": "The second aim of the constitutional law is to defend Slovak family law from the interference of international organizations and the attempt to equate marriage with other forms of non-marital cohabitation that do not have the support of the Slovak public."}
Output: {"ID": 5599, "QuasiSentence": "The second aim of the constitutional law is to defend Slovak family law from the interference of international organizations and the attempt to equate marriage with other forms of non-marital cohabitation that do not have the support of the Slovak public.", "Code": 1}

Input: {"ID": 613, "QuasiSentence": "4.Repeal the Gender Equality Act and the system of gender equality ombudsmen."}
Output: {"ID": 613, "QuasiSentence": "4.Repeal the Gender Equality Act and the system of gender equality ombudsmen.", "Code": 1}

Input: {"ID": 48104, "QuasiSentence": "More than half of all women seeking refuge from domestic violence in women's shelters are migrants."}
Output: {"ID": 48104, "QuasiSentence": "More than half of all women seeking refuge from domestic violence in women's shelters are migrants.", "Code": 0}

Input: {"ID": 18391, "QuasiSentence": "Strengthening women's organizations in the social partnership"}
Output: {"ID": 18391, "QuasiSentence": "Strengthening women's organizations in the social partnership", "Code": -1}

Input: {"ID": 33972, "QuasiSentence": "The Office will need to focus on active cooperation with women's NGOs, parties and trade unions, and will therefore need a larger share of the state budget"}
Output: {"ID": 33972, "QuasiSentence": "The Office will need to focus on active cooperation with women's NGOs, parties and trade unions, and will therefore need a larger share of the state budget", "Code": -1}

Input: {"ID": 2324, "QuasiSentence": "For example, government subsidies and tax breaks for daycare discriminate against the traditional family."}
Output: {"ID": 2324, "QuasiSentence": "For example, government subsidies and tax breaks for daycare discriminate against the traditional family.", "Code": 99}

NOW CLASSIFY:
ID {ID}
QuasiSentence: "{sentence}"
""",
    },
}

# ---------------------------------------------------------------------------
# Dynamic dimension loading — persists to data/dimensions.json
# ---------------------------------------------------------------------------

DIMENSIONS_CONFIG_PATH = os.path.join(DATA_DIR, "dimensions.json")


def load_dimensions() -> dict:
    """Load dimensions from dimensions.json if present, else fall back to built-in defaults."""
    if os.path.exists(DIMENSIONS_CONFIG_PATH):
        try:
            with open(DIMENSIONS_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {k: dict(v) for k, v in _DEFAULT_DIMENSIONS.items()}


DIMENSIONS = load_dimensions()
