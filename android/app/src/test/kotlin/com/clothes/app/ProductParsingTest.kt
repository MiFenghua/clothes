package com.clothes.app

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test

class ProductParsingTest {
    @Test
    fun parseProfileViewMapsNullUserAndStyleProfile() {
        val json = JSONObject(
            """
            {
              "user": null,
              "style_profile": {
                "display_name": "Ada",
                "height_cm": 168,
                "weight_kg": null,
                "body_shape": "pear",
                "skin_tone": "warm",
                "hair_tone": "brown",
                "style_keywords": ["minimal", "commute"],
                "feature_metrics": [
                  {"label": "height", "value": "168 cm"}
                ]
              }
            }
            """.trimIndent(),
        )

        val view = parseProfileView(json)

        assertNull(view.user)
        assertEquals("Ada", view.styleProfile.displayName)
        assertEquals(168, view.styleProfile.heightCm)
        assertNull(view.styleProfile.weightKg)
        assertEquals(listOf("minimal", "commute"), view.styleProfile.styleKeywords)
        assertEquals("height", view.styleProfile.featureMetrics.first().label)
        assertEquals("168 cm", view.styleProfile.featureMetrics.first().value)
    }

    @Test
    fun parseHomeViewMapsSummaryRecommendationsSuggestionAndStatus() {
        val json = JSONObject(
            """
            {
              "feature_summary": {
                "score": 0.88,
                "title": "Balanced",
                "summary": "Clean lines"
              },
              "recommendations": [
                {
                  "recommendation_id": "rec-1",
                  "title": "Blue blazer",
                  "scene": "commute",
                  "score": 0.93,
                  "image_url": "https://example.com/rec.png",
                  "source_task_id": null
                }
              ],
              "today_suggestion": {
                "title": "Layer lightly",
                "body": "Use a thin knit."
              },
              "backend_status": {
                "online": true,
                "queue": 2,
                "last_error": null
              }
            }
            """.trimIndent(),
        )

        val view = parseHomeView(json)

        assertEquals(0.88, view.featureSummary.score, 0.0001)
        assertEquals("rec-1", view.recommendations.single().recommendationId)
        assertEquals("Blue blazer", view.recommendations.first().title)
        assertEquals("https://example.com/rec.png", view.recommendations.single().imageUrl)
        assertNull(view.recommendations.first().sourceTaskId)
        assertEquals("Layer lightly", view.todaySuggestion.title)
        assertEquals("true", view.backendStatus["online"])
        assertEquals("2", view.backendStatus["queue"])
        assertFalse(view.backendStatus.containsKey("last_error"))
    }

    @Test
    fun parseInspirationPageMapsItemsAndCursor() {
        val json = JSONObject(
            """
            {
              "items": [
                {
                  "inspiration_id": "insp-1",
                  "title": "Office neutral",
                  "scene": "commute",
                  "palette": "ivory / navy",
                  "note": "Soft contrast",
                  "score": 0.86,
                  "image_url": "https://example.com/insp.png",
                  "favorite_id": "fav-1"
                }
              ],
              "next_cursor": "cursor-2"
            }
            """.trimIndent(),
        )

        val page = parseInspirationPage(json)

        assertEquals("cursor-2", page.nextCursor)
        assertEquals("Office neutral", page.items.single().title)
        assertEquals("insp-1", page.items.single().inspirationId)
        assertEquals("https://example.com/insp.png", page.items.single().imageUrl)
        assertEquals("fav-1", page.items.single().favoriteId)
    }

    @Test
    fun parseFavoriteMapsSnapshotTitle() {
        val favorite = parseFavorite(
            JSONObject(
                """
                {
                  "favorite_id": "fav-1",
                  "owner_id": null,
                  "favorite_type": "inspiration",
                  "target_id": "insp-1",
                  "snapshot": {
                    "title": "Office neutral"
                  }
                }
                """.trimIndent(),
            ),
        )

        assertEquals("fav-1", favorite.favoriteId)
        assertNull(favorite.ownerId)
        assertEquals("inspiration", favorite.favoriteType)
        assertEquals("insp-1", favorite.targetId)
        assertEquals("Office neutral", favorite.snapshotTitle)

        val list = parseFavorites(JSONArray().put(JSONObject().put("favorite_id", "fav-2")))
        assertEquals("fav-2", list.single().favoriteId)
    }
}
