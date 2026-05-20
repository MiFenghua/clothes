package com.clothes.app

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import android.provider.OpenableColumns
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.DataOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

class StyleApi(
    private val context: Context,
    private val baseUrl: String,
) {
    suspend fun health(): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            val connection = openConnection("/health", "GET")
            try {
                readResponse(connection)
                true
            } finally {
                connection.disconnect()
            }
        }.getOrDefault(false)
    }

    suspend fun createTask(photoUri: Uri, form: StyleForm): StyleTaskView = withContext(Dispatchers.IO) {
        val boundary = "ClothesBoundary${System.currentTimeMillis()}"
        val connection = openConnection("/api/v1/style-tasks", "POST").apply {
            doOutput = true
            setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        }
        try {
            DataOutputStream(connection.outputStream).use { output ->
                writeField(output, boundary, "scene", form.scene)
                writeField(output, boundary, "budget_min", form.budgetMin)
                writeField(output, boundary, "budget_max", form.budgetMax)
                writeField(output, boundary, "liked_style", buildLikedStyle(form))
                writeField(output, boundary, "avoid", form.avoid)
                writeField(output, boundary, "age_years", form.ageYears)
                writeField(output, boundary, "height_cm", form.heightCm)
                writeField(output, boundary, "weight_kg", form.weightKg)
                writeField(output, boundary, "usual_size", form.usualSize)
                writeField(output, boundary, "marketplaces", form.marketplaces)
                writeField(output, boundary, "wardrobe_item_ids", form.wardrobeItemIds)
                writeFile(output, boundary, "photo", photoUri)
                output.writeBytes("--$boundary--\r\n")
            }
            normalizeTaskView(parseTaskView(readResponse(connection)))
        } finally {
            connection.disconnect()
        }
    }

    suspend fun getTask(taskId: String): StyleTaskView = withContext(Dispatchers.IO) {
        val connection = openConnection("/api/v1/style-tasks/$taskId", "GET")
        try {
            normalizeTaskView(parseTaskView(readResponse(connection)))
        } finally {
            connection.disconnect()
        }
    }

    suspend fun getResult(taskId: String): StyleTaskResult = withContext(Dispatchers.IO) {
        val connection = openConnection("/api/v1/style-tasks/$taskId/result", "GET")
        try {
            normalizeResult(parseResult(JSONObject(readResponse(connection))))
        } finally {
            connection.disconnect()
        }
    }

    suspend fun retryImage(taskId: String): StyleTaskView = withContext(Dispatchers.IO) {
        val connection = openConnection("/api/v1/style-tasks/$taskId/retry-image", "POST").apply {
            doOutput = true
            setRequestProperty("Content-Length", "0")
        }
        try {
            normalizeTaskView(parseTaskView(readResponse(connection)))
        } finally {
            connection.disconnect()
        }
    }

    suspend fun listWardrobeItems(): List<WardrobeItem> = withContext(Dispatchers.IO) {
        val connection = openConnection("/api/v1/wardrobe-items", "GET")
        try {
            parseWardrobeItems(JSONArray(readResponse(connection))).map(::normalizeWardrobeItem)
        } finally {
            connection.disconnect()
        }
    }

    suspend fun createWardrobeItem(draft: WardrobeDraft): WardrobeItem = withContext(Dispatchers.IO) {
        val photoUri = draft.photoUri ?: error("请先选择衣物照片")
        val boundary = "WardrobeBoundary${System.currentTimeMillis()}"
        val connection = openConnection("/api/v1/wardrobe-items", "POST").apply {
            doOutput = true
            setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        }
        try {
            DataOutputStream(connection.outputStream).use { output ->
                writeField(output, boundary, "category", draft.category)
                writeField(output, boundary, "title", draft.title)
                writeField(output, boundary, "colors", draft.colors)
                writeField(output, boundary, "style_tags", draft.styleTags)
                writeField(output, boundary, "fit_tags", draft.fitTags)
                writeField(output, boundary, "notes", draft.notes)
                writeFile(output, boundary, "photo", photoUri)
                output.writeBytes("--$boundary--\r\n")
            }
            normalizeWardrobeItem(parseWardrobeItem(JSONObject(readResponse(connection))))
        } finally {
            connection.disconnect()
        }
    }

    suspend fun saveImageToGallery(imageUrl: String): Boolean = withContext(Dispatchers.IO) {
        val bytes = readImageBytes(normalizeAssetUrl(imageUrl)) ?: return@withContext false
        val resolver = context.contentResolver
        val name = "clozai_${System.currentTimeMillis()}.png"
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, name)
            put(MediaStore.Images.Media.MIME_TYPE, "image/png")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/clozAi")
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
        }
        val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values) ?: return@withContext false
        resolver.openOutputStream(uri)?.use { it.write(bytes) } ?: return@withContext false
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            values.clear()
            values.put(MediaStore.Images.Media.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
        }
        true
    }

    private fun openConnection(path: String, method: String): HttpURLConnection {
        return (URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 20000
            readTimeout = 120000
            setRequestProperty("Accept", "application/json")
        }
    }

    private fun writeField(output: DataOutputStream, boundary: String, name: String, value: String?) {
        if (value.isNullOrBlank()) return
        output.writeBytes("--$boundary\r\n")
        output.writeBytes("Content-Disposition: form-data; name=\"$name\"\r\n\r\n")
        output.write(value.toByteArray(Charsets.UTF_8))
        output.writeBytes("\r\n")
    }

    private fun writeFile(output: DataOutputStream, boundary: String, fieldName: String, uri: Uri) {
        val fileName = displayName(uri) ?: "photo.jpg"
        val mime = context.contentResolver.getType(uri) ?: "image/jpeg"
        output.writeBytes("--$boundary\r\n")
        output.writeBytes("Content-Disposition: form-data; name=\"$fieldName\"; filename=\"$fileName\"\r\n")
        output.writeBytes("Content-Type: $mime\r\n\r\n")
        context.contentResolver.openInputStream(uri)?.use { input ->
            input.copyTo(output)
        }
        output.writeBytes("\r\n")
    }

    private fun displayName(uri: Uri): String? {
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0 && cursor.moveToFirst()) {
                return cursor.getString(index)
            }
        }
        return null
    }

    private fun readResponse(connection: HttpURLConnection): String {
        val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
        val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
        if (connection.responseCode !in 200..299) {
            throw IllegalStateException(errorMessage(text).ifBlank { "请求失败：${connection.responseCode}" })
        }
        return text
    }

    private fun errorMessage(text: String): String {
        return runCatching {
            val json = JSONObject(text)
            json.optString("detail").ifBlank {
                json.optJSONObject("error")?.optString("message").orEmpty()
            }
        }.getOrDefault("")
    }

    private fun readImageBytes(imageUrl: String): ByteArray? {
        if (imageUrl.startsWith("data:image/svg", ignoreCase = true)) return null
        if (imageUrl.startsWith("data:", ignoreCase = true)) {
            val encoded = imageUrl.substringAfter("base64,", "")
            return encoded.takeIf { it.isNotBlank() }?.let { android.util.Base64.decode(it, android.util.Base64.DEFAULT) }
        }
        return URL(imageUrl).openStream().use { it.readBytes() }
    }

    private fun buildLikedStyle(form: StyleForm): String {
        return listOf(form.likedStyle, form.bodyShape, form.skinTone, form.hairTone)
            .filter { it.isNotBlank() }
            .joinToString(",")
    }

    private fun normalizeTaskView(task: StyleTaskView): StyleTaskView {
        return task.copy(result = task.result?.let(::normalizeResult))
    }

    private fun normalizeResult(result: StyleTaskResult): StyleTaskResult {
        return result.copy(
            tryOnImageUrl = result.tryOnImageUrl?.let(::normalizeAssetUrl),
            outfit = result.outfit?.let(::normalizeOutfit),
            alternativesRejected = result.alternativesRejected.map(::normalizeOutfit),
        )
    }

    private fun normalizeOutfit(outfit: OutfitCandidate): OutfitCandidate {
        return outfit.copy(items = outfit.items.map(::normalizeOutfitItem))
    }

    private fun normalizeOutfitItem(item: OutfitItem): OutfitItem {
        return item.copy(imageUrl = normalizeAssetUrl(item.imageUrl))
    }

    private fun normalizeWardrobeItem(item: WardrobeItem): WardrobeItem {
        return item.copy(imageUrl = normalizeAssetUrl(item.imageUrl))
    }

    private fun normalizeAssetUrl(url: String): String {
        val hostBase = baseUrl.trimEnd('/')
        return url
            .replace("http://127.0.0.1:8000", hostBase)
            .replace("http://localhost:8000", hostBase)
    }
}

fun parseTaskView(text: String): StyleTaskView {
    val json = JSONObject(text)
    return StyleTaskView(
        taskId = json.optString("task_id"),
        status = json.optString("status"),
        progress = json.optInt("progress"),
        message = json.optString("message"),
        result = json.optJSONObject("result")?.let(::parseResult),
        error = json.optNullableString("error"),
    )
}

fun parseResult(json: JSONObject): StyleTaskResult {
    return StyleTaskResult(
        taskId = json.optString("task_id"),
        status = json.optString("status"),
        outfit = json.optJSONObject("outfit")?.let(::parseOutfit),
        tryOnImageUrl = json.optNullableString("try_on_image_url"),
        recommendationReport = json.optJSONObject("recommendation_report")?.let(::parseRecommendationReport),
        imageQualityReport = json.optJSONObject("image_quality_report")?.let(::parseImageQualityReport),
        alternativesRejected = json.optJSONArray("alternatives_rejected").toObjectList(::parseOutfit),
        userMessage = json.optNullableString("user_message"),
    )
}

fun parseOutfit(json: JSONObject): OutfitCandidate {
    return OutfitCandidate(
        candidateId = json.optString("candidate_id"),
        title = json.optString("title"),
        items = json.optJSONArray("items").toObjectList(::parseOutfitItem),
        totalPrice = json.optDouble("total_price"),
        score = json.optDouble("score"),
        scoreBreakdown = json.optJSONObject("score_breakdown").toDoubleMap(),
        whyThisWorks = json.optJSONArray("why_this_works").toStringList(),
        whyNotOthers = json.optJSONArray("why_not_others").toStringList(),
        riskFlags = json.optJSONArray("risk_flags").toStringList(),
    )
}

fun parseOutfitItem(json: JSONObject): OutfitItem {
    return OutfitItem(
        productId = json.optString("product_id"),
        marketplace = json.optString("marketplace"),
        category = json.optString("category"),
        title = json.optString("title"),
        price = json.optDouble("price"),
        priceText = json.optNullableString("price_text"),
        imageUrl = json.optString("image_url"),
        productUrl = json.optString("product_url"),
        shopName = json.optNullableString("shop_name"),
        selectionReason = json.optString("selection_reason"),
        matchReason = json.optString("match_reason"),
    )
}

fun parseRecommendationReport(json: JSONObject): RecommendationReport {
    return RecommendationReport(
        finalScore = json.optDouble("final_score"),
        fitScore = json.optDouble("fit_score"),
        colorScore = json.optDouble("color_score"),
        occasionScore = json.optDouble("occasion_score"),
        budgetScore = json.optDouble("budget_score"),
        wardrobeScore = json.optDouble("wardrobe_score"),
        gates = json.optJSONArray("gates").toObjectList(::parseGate),
        riskFlags = json.optJSONArray("risk_flags").toStringList(),
        whyThisWorks = json.optJSONArray("why_this_works").toStringList(),
        whyNotOthers = json.optJSONArray("why_not_others").toStringList(),
    )
}

fun parseImageQualityReport(json: JSONObject): ImageQualityReport {
    return ImageQualityReport(
        candidateId = json.optString("candidate_id"),
        overallScore = json.optDouble("overall_score"),
        identityScore = json.optDouble("identity_score"),
        garmentScore = json.optDouble("garment_score"),
        artifactScore = json.optDouble("artifact_score"),
        realismScore = json.optDouble("realism_score"),
        gates = json.optJSONArray("gates").toObjectList(::parseGate),
        accepted = json.optBoolean("accepted"),
        retryPromptHint = json.optNullableString("retry_prompt_hint"),
    )
}

fun parseGate(json: JSONObject): QualityGateReport {
    return QualityGateReport(
        gate = json.optString("gate"),
        status = json.optString("status"),
        score = json.optDouble("score"),
        reasons = json.optJSONArray("reasons").toStringList(),
        blocking = json.optBoolean("blocking"),
    )
}

fun parseWardrobeItems(json: JSONArray): List<WardrobeItem> {
    return List(json.length()) { index -> parseWardrobeItem(json.getJSONObject(index)) }
}

fun parseWardrobeItem(json: JSONObject): WardrobeItem {
    return WardrobeItem(
        itemId = json.optString("item_id"),
        category = json.optString("category"),
        imageUrl = json.optString("image_url"),
        title = json.optString("title"),
        colors = json.optJSONArray("colors").toStringList(),
        styleTags = json.optJSONArray("style_tags").toStringList(),
        fitTags = json.optJSONArray("fit_tags").toStringList(),
        notes = json.optNullableString("notes"),
    )
}

private fun JSONObject?.toDoubleMap(): Map<String, Double> {
    if (this == null) return emptyMap()
    val result = linkedMapOf<String, Double>()
    keys().forEach { key -> result[key] = optDouble(key) }
    return result
}

private fun JSONArray?.toStringList(): List<String> {
    if (this == null) return emptyList()
    return List(length()) { index -> optString(index) }.filter { it.isNotBlank() }
}

private fun <T> JSONArray?.toObjectList(parser: (JSONObject) -> T): List<T> {
    if (this == null) return emptyList()
    return List(length()) { index -> parser(getJSONObject(index)) }
}

private fun JSONObject.optNullableString(name: String): String? {
    if (!has(name) || isNull(name)) return null
    return optString(name).takeIf { it.isNotBlank() }
}

fun Double.asPercent(): String = String.format(Locale.US, "%.0f%%", this * 100)
