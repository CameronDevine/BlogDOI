import os
import sys
from copy import copy
from pypandoc import convert_file

from nikola.plugin_categories import Task
from nikola import utils

sys.path.insert(0, os.path.dirname(__file__))
from common import *


def update_deps(post, lang, task):
    """Update file dependencies as they might have been updated during compilation.
    This is done for example by the ReST page compiler, which writes its
    dependencies into a .dep file. This file is read and incorporated when calling
    post.fragment_deps(), and only available /after/ compiling the fragment.
    """
    task.file_dep.update(
        [p for p in post.fragment_deps(lang) if not p.startswith("####MAGIC####")]
    )


class PostPDF(Task):
    name = "post_pdf"

    def gen_tasks(self):
        self.site.scan_posts()
        kw = {
            "translations": self.site.config["TRANSLATIONS"],
            "timeline": self.site.timeline,
            "default_lang": self.site.config["DEFAULT_LANG"],
            "show_untranslated_posts": self.site.config["SHOW_UNTRANSLATED_POSTS"],
            "demote_headers": self.site.config["DEMOTE_HEADERS"],
        }
        self.tl_changed = False
        yield self.group_task()

        def tl_ch():
            self.tl_changed = True

        yield {
            "basename": self.name,
            "name": "timeline_changes",
            "actions": [tl_ch],
            "uptodate": [utils.config_changed({1: kw["timeline"]})],
        }
        for lang in kw["translations"]:
            deps_dict = copy(kw)
            deps_dict.pop("timeline")
            for post in kw["timeline"]:
                if not should_generate_pdf(self.site, post, lang):
                    self.logger.info("not generating pdf for " + post.title())
                    continue

                yield utils.apply_filters(
                    self.get_task(deps_dict, post, lang),
                    {
                        os.path.splitext(get_pdf_dest(self.site, post, lang))[
                            -1
                        ]: self.get_metadata_filters(post, lang)
                    },
                )

    def compile(self, post, lang, task):
        self.create_folder()
        convert_file(post.source_path, "pdf", outputfile=task.targets[0])

    def dependence_on_timeline(self, post, lang):
        """Check if a post depends on the timeline."""
        if "####MAGIC####TIMELINE" not in post.fragment_deps(lang):
            return True  # No dependency on timeline
        elif self.tl_changed:
            return False  # Timeline changed
        return True

    def create_folder(self):
        dir = os.path.join(self.site.config["OUTPUT_FOLDER"], "posts", "pdf")
        if not os.path.isdir(dir):
            os.mkdir(dir)

    def get_metadata_filters(self, post, lang):
        # Apply filters specified in the metadata
        ff = [x.strip() for x in post.meta("filters", lang).split(",")]
        flist = []
        for i, f in enumerate(ff):
            if not f:
                continue
            _f = self.site.filters.get(f)
            if _f is not None:  # A registered filter
                flist.append(_f)
            else:
                flist.append(f)
        return flist

    def get_task(self, deps_dict, post, lang):
        # Extra config dependencies picked from config
        for p in post.fragment_deps(lang):
            if p.startswith("####MAGIC####CONFIG:"):
                k = p.split("####MAGIC####CONFIG:", 1)[-1]
                deps_dict[k] = self.site.config.get(k)
        dest = get_pdf_dest(self.site, post, lang)
        file_dep = [
            p for p in post.fragment_deps(lang) if not p.startswith("####MAGIC####")
        ]
        self.logger.info(file_dep)
        return {
            "basename": self.name,
            "name": dest,
            "file_dep": file_dep,
            "targets": [dest],
            "actions": [
                (
                    self.compile,
                    (
                        post,
                        lang,
                    ),
                ),
                (
                    update_deps,
                    (
                        post,
                        lang,
                    ),
                ),
            ],
            "clean": True,
            "uptodate": [
                utils.config_changed(deps_dict, "nikola.plugins.task.posts"),
                lambda p=post, l=lang: self.dependence_on_timeline(p, l),
            ]
            + post.fragment_deps_uptodate(lang),
            "task_dep": ["render_posts:timeline_changes"],
        }
