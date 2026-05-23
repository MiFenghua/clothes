import type { Outfit } from "../domain/types.js";

export class ImageDirector {
  buildPrompt(outfit: Outfit) {
    return `Create a realistic full-body fashion try-on image.

Use the uploaded person photo as the identity and body reference.
Preserve the person's face, facial structure, hairstyle, skin tone, body proportions, and overall identity.
The pose may be adjusted to a natural fashion lookbook pose, but the person should still look like the same person.

Dress the person in the selected outfit:
${outfit.tryOnDescription}

Use the product images as visual references for color, silhouette, material, and garment details.
Keep the outfit faithful to the product images.
Generate a polished full-body try-on preview with clean lighting.
Do not over-sexualize the person.
Do not change the person's age, ethnicity, body type, or facial identity.
Do not add extra garments that are not part of the selected outfit.`;
  }
}
