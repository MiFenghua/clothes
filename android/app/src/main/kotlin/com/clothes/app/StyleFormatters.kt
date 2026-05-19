package com.clothes.app

fun categoryLabel(value: String): String = when (value) {
    "top" -> "上衣"
    "bottom" -> "下装"
    "dress" -> "裙装"
    "outerwear" -> "外套"
    "shoes" -> "鞋履"
    "bag" -> "包袋"
    "accessory" -> "配饰"
    else -> value
}

fun platformLabel(value: String): String = when (value) {
    "taobao" -> "淘宝"
    "tmall" -> "天猫"
    "amazon" -> "Amazon"
    "jd" -> "京东"
    "pdd" -> "拼多多"
    "owned" -> "衣橱"
    else -> value
}
