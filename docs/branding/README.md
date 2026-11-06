# Vacuula Client artwork

I use the robot-vacuum illustration supplied as `5800.jpg` for this independent
integration. I cropped the image to its pale blue rounded-square tile, removed
the outer white background and cleaned the transparent edges. The processed
master is preserved as [`robot-vacuum.png`](robot-vacuum.png).

The packaged icons include an [artwork notice](../../custom_components/vacuula_client/brand/NOTICE.txt).
Product names identify the connected project and do not imply endorsement.

## Packaged images

| File | Dimensions | Format |
| --- | --- | --- |
| `custom_components/vacuula_client/brand/icon.png` | 256 × 256 | Transparent, lossless, interlaced RGBA PNG |
| `custom_components/vacuula_client/brand/icon@2x.png` | 512 × 512 | Transparent, lossless, interlaced RGBA PNG |

The square artwork serves as both icon and logo. The
[Home Assistant branding guide](https://contributors.home-assistant.io/core/integrations/brands/)
asks for icon files only in this case; Home Assistant provides logo and dark-theme
fallbacks. The pale blue tile keeps the robot legible on light and dark backgrounds,
so separate dark images are unnecessary. The outer corners are transparent.

Custom integrations bundle these files in `brand/` on Home Assistant 2026.3 and
newer. They take precedence over CDN images without a manifest setting or a
central brands submission. If the integration is later contributed to Core,
the assets must move to the central brands repository.

## Reproduce the PNGs

Run from the repository root with ImageMagick 7.1.2 installed. The processed
master preserves the crop and transparency so resizing needs no background tools:

```sh
magick docs/branding/robot-vacuum.png -filter Lanczos -resize 512x512 \
  -strip -define png:compression-level=9 -interlace PNG \
  PNG32:custom_components/vacuula_client/brand/icon@2x.png
magick docs/branding/robot-vacuum.png -filter Lanczos -resize 256x256 \
  -strip -define png:compression-level=9 -interlace PNG \
  PNG32:custom_components/vacuula_client/brand/icon.png
```

## Verify the local installation

Restart Home Assistant after updating the integration. Authenticated requests to
`/api/brands/integration/vacuula_client/icon.png?placeholder=no` and
`/api/brands/integration/vacuula_client/icon@2x.png?placeholder=no` must return HTTP 200
and bytes matching the installed PNGs. Check the `logo` and `dark_` fallback
requests too. `placeholder=no` prevents a generic placeholder from being
mistaken for a successful branding installation.
