import os
from nikola import utils


def get_pdf_dest(site, post, lang):
    base_path = os.path.join(
        site.config["OUTPUT_FOLDER"],
        "posts",
        "pdf",
        utils.slugify(post.title()),
    )
    dest = base_path + ".pdf"
    if lang != site.default_lang:
        dest = site.config["TRANSLATIONS_PATTERN"].format(
            path=base_path, lang=lang, ext="pdf"
        )
    return dest


def should_generate_pdf(site, post, lang=None):
    deploy_drafts = site.config.get("DEPLOY_DRAFTS")
    deploy_future = site.config.get("DEPLOY_FUTURE")
    if not post.is_post:
        utils.LOGGER.info(post.title() + " is not a post")
        return False
    if not (
        lang is None
        or (
            post.is_translation_available(lang)
            or site.config["SHOW_UNTRANSLATED_POSTS"]
        )
    ):
        utils.LOGGER.info(
            "translation to " + lang + " not available for " + post.title()
        )
        return False
    if (not deploy_drafts and post.is_draft) or (deploy_future and post.publish_later):
        # Building the pdf would result in it getting deployed.
        # I don't know when the deployed signal handler is run before or after deployment,
        # but either way it is only run where there are new posts.
        return False
    return True
