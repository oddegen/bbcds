# Model Training

This guide runs the BBCDS MobileNetV3-Small research baseline on a free Google
Colab GPU. You do not need a local GPU.

The selected dataset is sensitive and gated. Continue only if you are an adult,
access is lawful where you live, and you accept the dataset terms. The
[`deepghs/nsfw_detect` dataset card](https://huggingface.co/datasets/deepghs/nsfw_detect)
declares MIT at the repository level, but it does not document provenance,
consent, or training rights for every underlying image. A model trained with it
is a research baseline, not a commercially cleared release.

Colab provides free GPU access, but GPU type, availability, usage limits, idle
timeouts, and runtime duration are not guaranteed. Free notebooks can run for
at most 12 hours depending on availability and usage. See the
[Google Colab FAQ](https://research.google.com/colaboratory/faq.html).

## Before You Start

1. Create or sign in to a Google account.
2. Create or sign in to a [Hugging Face account](https://huggingface.co/join).
3. Open the [dataset page](https://huggingface.co/datasets/deepghs/nsfw_detect),
   review the warning and conditions, and request or accept access.
4. Create a read-only token in
   [Hugging Face settings](https://huggingface.co/settings/tokens).
5. Push the current repository changes to GitHub so Colab can load the same
   training code. A public repository needs no GitHub token. A private
   repository needs a read-only GitHub token.

Do not put the downloaded dataset, extracted images, or protected CSV manifest
in Google Drive. Only checkpoints, logs, aggregate metrics, and validation
evidence belong there. Review the
[Google Drive abuse policy](https://support.google.com/docs/answer/148505?hl=en)
before storing sensitive material.

## Run In Colab

1. Open [`model/notebooks/train-colab.ipynb`](../model/notebooks/train-colab.ipynb)
   in Google Colab.
2. Select **Runtime > Change runtime type**, choose **T4 GPU**, and save.
3. Open the key-shaped **Secrets** panel on the left.
4. Add a secret named `HF_TOKEN`, paste the read-only Hugging Face token, and
   enable notebook access.
5. For a private GitHub repository, also add `GITHUB_TOKEN` with read-only
   repository access and enable notebook access.
6. Run each cell in order with its play button. Wait for a cell to finish before
   running the next one.
7. Confirm the first cell prints GPU information.
8. Confirm the manifest audit shows aggregate counts for every class and all
   three splits. It must not display images or source filenames.
9. Approve the Google Drive mount when prompted.
10. Start the training cell. It writes recoverable state to
    `MyDrive/bbcds-runs/mobilenet-v3-small-v1`.

The download is currently about 1.8 GB. It is stored only in Colab's temporary
`/content/bbcds-data` directory. The manifest command maps the source folders as
follows:

| Source folder        | BBCDS label             |
| -------------------- | ----------------------- |
| `neutral`, `drawing` | `Safe`                  |
| `sexy`               | `Suggestive`            |
| `porn`               | `Explicit`              |
| `hentai`             | `Explicit Illustration` |

Preparation verifies each supported image with Pillow, computes SHA-256 and a
perceptual hash, removes exact duplicates, groups near-duplicates, excludes
conflicting-label groups, and assigns each group deterministically to 80%
training, 10% validation, or 10% test.

## Recover An Interrupted Run

1. Reopen the notebook and attach a GPU runtime.
2. Add or re-enable the same Colab Secrets.
3. Run the cells from the top.
4. Mount the same Google Drive.
5. Run the training cell unchanged.

The `--resume` option loads the newest completed training checkpoint, while
Keras backup state recovers an interrupted fit. Do not rename the Drive output
folder between attempts. Colab may still make you wait before another free GPU
is available.

If training reports GPU memory exhaustion, change `--batch-size` from `64` to
`32` in the training cell and run it again.

## Finish Safely

1. Confirm Drive contains `final.keras`, `run-metadata.json`,
   `baseline-validation-draft.json`, and both training logs.
2. Run the cleanup cell to remove `/content/bbcds-data`, including the images
   and protected manifest.
3. Select **Runtime > Disconnect and delete runtime**.
4. Keep all Drive outputs private. Do not commit them to Git.
5. Review only aggregate evidence before updating the model card or data card.

## Contract

- Architecture: MobileNetV3-Small.
- Input: RGB, `1 x 224 x 224 x 3`, float32, `[0,255]`.
- Preprocessing: aspect-preserving letterbox to 224 by 224; MobileNetV3
  preprocessing remains inside the Keras model.
- Output: four float32 probabilities ordered as `Safe`, `Suggestive`,
  `Explicit`, `Explicit Illustration`.

## Current Boundary

This tooling stops at Keras training and protected validation evidence. TFLite
export, post-training quantization, metadata embedding, LiteRT.js compatibility
testing, browser inference, and video sampling are outside this workflow unless
an ADR changes the roadmap.
