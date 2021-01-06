from nikola.plugin_categories import Command
from nikola import utils
from hashlib import md5
import os
import json
from time import sleep
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import *
from zenodo import Zenodo


class Deposit(Command):

    name = "deposit"
    doc_usage = "[options]"
    doc_purpose = "Depost posts to Zenodo."

    cmd_options = (
        {
            "name": "deposit",
            "long": "deposit",
            "short": "",
            "default": False,
            "type": bool,
            "help": "Actually deposit to Zenodo.",
        },
        {
            "name": "sandbox",
            "long": "sandbox",
            "short": "s",
            "default": False,
            "type": bool,
            "help": "Deposit to Zenodo sandbox.",
        },
    )

    title_deliminator = " - "

    def _execute(self, options, args):
        if not (options.get("deposit") or options.get("sandbox")):
            print("You must use the --depsoit option for this command to do anything.")
            return
        zenodo_token = os.environ.get("ZENODO_TOKEN")
        zenodo_url = "zenodo.org"
        if options.get("sandbox"):
            zenodo_url = "sandbox.zenodo.org"
            zenodo_token = os.environ.get("ZENODO_SANDBOX_TOKEN")
        if not zenodo_token:
            print("Please set the ZENODO_TOKEN environment variable.")
            return
        self.site.scan_posts()
        zenodo = Zenodo(zenodo_token, zenodo_url)
        depositions = zenodo.get_depositions()
        print("got existing depositions")
        for post in self.site.timeline:
            if not should_generate_pdf(self.site, post):
                print("not depositing " + post.title())
                continue
            deposition_found = False
            for deposition in depositions:
                if deposition.title.startswith(self.get_deposition_title_head(post)):
                    deposition_found = True
                    print("found deposition for " + post.title())
                    break
            if not deposition_found:
                deposition = zenodo.create_deposition(self.get_metadata(post))
            up_to_date = self.up_to_date(
                self.get_archive_checksums(deposition), self.get_source_checksums(post)
            )
            if up_to_date and deposition.submitted:
                print("up to date")
                continue
            if deposition.submitted:
                print("creating new version")
                deposition = deposition.newversion()
                deposition.latest_draft()
            if not up_to_date:
                print("not up to date")
                for file in deposition.files():
                    file.delete()
                for path in self.get_pdf_files(post):
                    _, filename = os.path.split(path)
                    with open(path, "rb") as f:
                        deposition.add_file(filename, f)
            deposition.update_metadata(
                self.get_metadata(post, json.dumps(self.get_source_checksums(post)))
            )
            deposition.publish()

    def get_deposition_title_head(self, post):
        return self.title_deliminator.join(
            (
                self.site.config["BLOG_TITLE"](),
                post.formatted_date(self.site.config["DATE_FORMAT"]),
            )
        )

    def get_deposition_title(self, post):
        return self.title_deliminator.join(
            (self.get_deposition_title_head(post), post.title())
        )

    def get_metadata(self, post, notes=None):
        metadata = {
            "upload_type": "publication",
            "publication_type": "other",
            "publication_date": post.formatted_date("webiso"),
            "title": self.get_deposition_title(post),
            "access_right": "open",
            "license": self.site.config.get("ZENODO_LICENSE", "cc-by"),
            "creators": [{"name": author} for author in post.authors()],
            "description": post.title(),
        }
        if notes:
            metadata["notes"] = notes
        return metadata

    def get_pdf_files(self, post):
        return [
            get_pdf_dest(self.site, post, lang)
            for lang in self.site.config["TRANSLATIONS"]
        ]

    def get_source_checksums(self, post):
        checksums = {}
        for lang in self.site.config["TRANSLATIONS"]:
            _, filename = os.path.split(get_pdf_dest(self.site, post, lang))
            checksums[filename] = md5(post.source(lang).encode("utf-8")).hexdigest()
        return checksums

    def get_archive_checksums(self, deposition):
        return json.loads(deposition.metadata.get("notes", "{}"))

    def up_to_date(self, archive, source):
        up_to_date = len(archive) == len(source)
        if up_to_date:
            for path, checksum in source.items():
                _, filename = os.path.split(path)
                up_to_date = archive.get(filename, "") == checksum
                if not up_to_date:
                    break
        return up_to_date
