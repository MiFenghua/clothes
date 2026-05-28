from __future__ import annotations

from dataclasses import dataclass

from app.schemas.domain import ProductCategory


@dataclass(frozen=True)
class TaobaoCategoryEntry:
    cid: str
    parent_cid: str
    terms: tuple[str, ...]


TAOBAO_CATEGORY_IDS: dict[str, str] = {
    "women_clothing": "16",
    "men_clothing": "30",
    "underwear_homewear": "1625",
    "women_shoes": "50006843",
    "men_shoes": "50011740",
    "sports_casual_clothing": "50010404",
    "kids_parent_child": "50008165",
    "bags_luggage": "50006842",
    "fashion_jewelry": "50013864",
    "watch": "50468001",
}


TAOBAO_CATEGORY_FALLBACKS: dict[ProductCategory, tuple[str, ...]] = {
    ProductCategory.top: (TAOBAO_CATEGORY_IDS["women_clothing"],),
    ProductCategory.bottom: (TAOBAO_CATEGORY_IDS["women_clothing"],),
    ProductCategory.dress: (TAOBAO_CATEGORY_IDS["women_clothing"],),
    ProductCategory.outerwear: (TAOBAO_CATEGORY_IDS["women_clothing"],),
    ProductCategory.shoes: (TAOBAO_CATEGORY_IDS["women_shoes"],),
    ProductCategory.bag: (TAOBAO_CATEGORY_IDS["bags_luggage"],),
    ProductCategory.accessory: (
        TAOBAO_CATEGORY_IDS["fashion_jewelry"],
        TAOBAO_CATEGORY_IDS["sports_casual_clothing"],
        TAOBAO_CATEGORY_IDS["watch"],
    ),
}


TAOBAO_CATEGORY_RULES: dict[ProductCategory, tuple[TaobaoCategoryEntry, ...]] = {
    ProductCategory.top: (
        TaobaoCategoryEntry("162104", "16", ("衬衫", "shirt", "blouse")),
        TaobaoCategoryEntry("162116", "16", ("雪纺", "蕾丝", "chiffon", "lace blouse")),
        TaobaoCategoryEntry("50000671", "16", ("t恤", "tee", "t-shirt", "tshirt")),
        TaobaoCategoryEntry("201241307", "16", ("polo", "polo衫")),
        TaobaoCategoryEntry("121412004", "16", ("吊带", "背心", "camisole", "tank top")),
        TaobaoCategoryEntry("50000697", "16", ("针织", "knit", "knitted")),
        TaobaoCategoryEntry("162103", "16", ("毛衣", "sweater")),
        TaobaoCategoryEntry("201405003", "16", ("羊绒", "cashmere")),
        TaobaoCategoryEntry("50008898", "16", ("卫衣", "sweatshirt", "hoodie")),
        TaobaoCategoryEntry("50022890", "50010404", ("瑜伽", "健身衣", "yoga", "training top")),
    ),
    ProductCategory.bottom: (
        TaobaoCategoryEntry("162205", "16", ("牛仔裤", "jeans", "denim pants")),
        TaobaoCategoryEntry("1623", "16", ("半身裙", "skirt")),
        TaobaoCategoryEntry("50007068", "16", ("打底裤", "leggings")),
        TaobaoCategoryEntry("202174802", "16", ("短裤", "shorts")),
        TaobaoCategoryEntry("162201", "16", ("休闲裤", "西装裤", "trousers", "pants")),
        TaobaoCategoryEntry("50023107", "50010404", ("运动长裤", "sweatpants", "track pants")),
        TaobaoCategoryEntry("50023108", "50010404", ("运动短裤", "sport shorts")),
        TaobaoCategoryEntry("126496001", "50010728", ("瑜伽裤", "yoga pants")),
        TaobaoCategoryEntry("126496002", "50010728", ("瑜伽短裤", "yoga shorts")),
    ),
    ProductCategory.dress: (
        TaobaoCategoryEntry("50010850", "16", ("连衣裙", "dress")),
        TaobaoCategoryEntry("50005065", "16", ("旗袍", "qipao", "cheongsam")),
        TaobaoCategoryEntry("162402", "16", ("西装套装", "职业套装", "suit set")),
        TaobaoCategoryEntry("123216004", "16", ("时尚套装", "套装", "two piece set")),
        TaobaoCategoryEntry("162404", "16", ("运动套装", "tracksuit")),
        TaobaoCategoryEntry("50008903", "16", ("jk制服", "制服", "school uniform")),
        TaobaoCategoryEntry("126496022", "50011699", ("洛丽塔连衣裙", "lolita dress")),
    ),
    ProductCategory.outerwear: (
        TaobaoCategoryEntry("50011277", "16", ("短外套", "外套", "jacket")),
        TaobaoCategoryEntry("50008897", "16", ("西装外套", "blazer")),
        TaobaoCategoryEntry("50008901", "16", ("风衣", "trench")),
        TaobaoCategoryEntry("50013194", "16", ("毛呢", "大衣", "wool coat", "coat")),
        TaobaoCategoryEntry("50008900", "16", ("棉服", "padded coat")),
        TaobaoCategoryEntry("50008899", "16", ("羽绒服", "down jacket")),
        TaobaoCategoryEntry("50011739", "50010404", ("运动外套", "track jacket")),
        TaobaoCategoryEntry("50011718", "50010404", ("运动风衣", "windbreaker")),
        TaobaoCategoryEntry("50014785", "50013886", ("冲锋衣", "shell jacket")),
    ),
    ProductCategory.shoes: (
        TaobaoCategoryEntry("50012042", "50006843", ("帆布鞋", "canvas shoes")),
        TaobaoCategoryEntry("201309706", "50006843", ("休闲板鞋", "板鞋", "sneakers")),
        TaobaoCategoryEntry("201309209", "50006843", ("乐福鞋", "loafers")),
        TaobaoCategoryEntry("201304009", "50006843", ("平底鞋", "flats")),
        TaobaoCategoryEntry("50012027", "50006843", ("浅口单鞋", "单鞋", "pumps")),
        TaobaoCategoryEntry("50012032", "50006843", ("凉鞋", "sandals")),
        TaobaoCategoryEntry("201304907", "50006843", ("休闲凉鞋", "casual sandals")),
        TaobaoCategoryEntry("50012028", "50006843", ("靴", "boots")),
        TaobaoCategoryEntry("201312704", "50006843", ("马丁靴", "martin boots")),
        TaobaoCategoryEntry("50012036", "50012029", ("跑步鞋", "running shoes")),
        TaobaoCategoryEntry("50012043", "50012029", ("运动休闲鞋", "sport shoes")),
    ),
    ProductCategory.bag: (
        TaobaoCategoryEntry("50012010", "50006842", ("女包", "手提包", "托特", "handbag", "tote")),
        TaobaoCategoryEntry("122690003", "50006842", ("双肩包", "backpack")),
        TaobaoCategoryEntry("121384005", "50006842", ("手机包", "phone bag")),
        TaobaoCategoryEntry("201241402", "50006842", ("胸包", "腰包", "belt bag")),
        TaobaoCategoryEntry("121434005", "50006842", ("钱包", "wallet")),
        TaobaoCategoryEntry("121400005", "50006842", ("卡包", "card holder")),
        TaobaoCategoryEntry("50050199", "50006842", ("旅行袋", "duffle")),
        TaobaoCategoryEntry("50012019", "50006842", ("行李箱", "suitcase")),
    ),
    ProductCategory.accessory: (
        TaobaoCategoryEntry("50013865", "50013864", ("项链", "necklace")),
        TaobaoCategoryEntry("50013868", "50013864", ("项坠", "吊坠", "pendant")),
        TaobaoCategoryEntry("50014238", "50013864", ("耳环", "earrings")),
        TaobaoCategoryEntry("50014239", "50013864", ("耳钉", "stud earrings")),
        TaobaoCategoryEntry("50024815", "50013864", ("耳夹", "ear clips")),
        TaobaoCategoryEntry("50013869", "50013864", ("手链", "bracelet")),
        TaobaoCategoryEntry("50013878", "50013864", ("发饰", "hair accessory")),
        TaobaoCategoryEntry("50013876", "50013864", ("胸针", "brooch")),
        TaobaoCategoryEntry("302910", "50010404", ("帽子", "hat", "cap")),
        TaobaoCategoryEntry("50007003", "50010404", ("围巾", "丝巾", "scarf")),
        TaobaoCategoryEntry("50009032", "50010404", ("腰带", "皮带", "belt")),
        TaobaoCategoryEntry("121454006", "50468001", ("手表", "腕表", "watch")),
        TaobaoCategoryEntry("50010368", "28", ("太阳镜", "墨镜", "sunglasses")),
    ),
}


BLOCKING_METADATA_TERMS = (
    "home goods",
    "household",
    "medical",
    "餐饮",
    "医疗",
    "居家日用",
    "家庭/个人清洁",
    "童装",
    "婴儿",
    "男装",
    "流行男鞋",
)

MAX_CAT_FILTER_IDS = 10


def taobao_category_filter(category: ProductCategory, query: str) -> str:
    matches = [
        entry.cid
        for entry in TAOBAO_CATEGORY_RULES.get(category, ())
        if _contains_any(query, entry.terms)
    ]
    if matches:
        return ",".join(_unique(matches)[:MAX_CAT_FILTER_IDS])
    try:
        return ",".join(TAOBAO_CATEGORY_FALLBACKS[category][:MAX_CAT_FILTER_IDS])
    except KeyError as exc:
        raise RuntimeError(f"Unsupported Taobao Union category: {category.value}") from exc


def taobao_category_match(
    *,
    category: ProductCategory,
    category_id: str,
    level_one_category_id: str,
    category_name: str,
    level_one_category_name: str,
) -> str:
    target_cids = _category_cids(category)
    target_parent_cids = _category_parent_cids(category)
    all_curated_cids = _all_curated_cids()

    if category_id and category_id in target_cids:
        return "exact"
    if level_one_category_id and level_one_category_id in target_parent_cids:
        return "broad"
    if category_id and category_id in all_curated_cids and category_id not in target_cids:
        return "mismatch"
    if level_one_category_id and level_one_category_id not in target_parent_cids:
        return "mismatch"

    metadata = f"{category_name} {level_one_category_name}".lower()
    if metadata:
        if _contains_any(metadata, _category_terms(category)):
            return "broad"
        if any(term.lower() in metadata for term in BLOCKING_METADATA_TERMS):
            return "mismatch"
    return "unknown"


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _category_cids(category: ProductCategory) -> set[str]:
    return {entry.cid for entry in TAOBAO_CATEGORY_RULES.get(category, ())}


def _category_parent_cids(category: ProductCategory) -> set[str]:
    parent_cids = {entry.parent_cid for entry in TAOBAO_CATEGORY_RULES.get(category, ())}
    parent_cids.update(TAOBAO_CATEGORY_FALLBACKS.get(category, ()))
    return parent_cids


def _all_curated_cids() -> set[str]:
    return {entry.cid for entries in TAOBAO_CATEGORY_RULES.values() for entry in entries}


def _category_terms(category: ProductCategory) -> tuple[str, ...]:
    terms: list[str] = []
    for entry in TAOBAO_CATEGORY_RULES.get(category, ()):
        terms.extend(entry.terms)
    return tuple(terms)
