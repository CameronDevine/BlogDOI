import requests


class Zenodo:
    transport = "https"
    base = ["api", "deposit", "depositions"]

    def __init__(self, token, host="zenodo.org"):
        self.host = host
        self.params = {"access_token": token}

    def build_url(self, *path):
        return (
            self.transport
            + "://"
            + self.host
            + "/"
            + "/".join(self.base + [str(el) for el in path])
        )

    def check_success(self, r, msg=""):
        if r.status_code // 100 != 2:
            raise ZenodoError(r.status_code, r.json(), msg)

    def get_depositions(self):
        r = requests.get(self.build_url(), params=self.params)
        self.check_success(r)
        return [ZenodoDeposition(self, d) for d in r.json()]

    def create_deposition(self, metadata={}):
        if isinstance(metadata, ZenodoMetadata):
            metadata = metadata.data
        r = requests.post(
            self.build_url(), params=self.params, json={"metadata": metadata}
        )
        self.check_success(r)
        return ZenodoDeposition(self, r.json())


class ZenodoError(Exception):
    def __init__(self, code, resp="", msg=""):
        self.code = code
        self.resp = resp
        self.msg = msg
        super().__init__("Zendo returned status code {}.".format(code))

    def __str__(self):
        return "Zenodo returned status code {}.\n{}\n{}".format(
            self.code, self.resp, self.msg
        ).strip()


class AttrDict:
    def __init__(self, data):
        self.data = data

    def __getattr__(self, name):
        return self.data[name]

    def get(self, name, default=None):
        try:
            val = self.data[name]
        except KeyError as e:
            if default is None:
                raise e
            val = default
        return val


class ZenodoDeposition(AttrDict):
    def __init__(self, zenodo, *args, **kwargs):
        self.zenodo = zenodo
        super().__init__(*args, **kwargs)

    @property
    def metadata(self):
        return ZenodoMetadata(self.data["metadata"])

    def files(self):
        r = requests.get(
            self.zenodo.build_url(self.id, "files"), params=self.zenodo.params
        )
        self.zenodo.check_success(r)
        return [ZenodoFile(self, f) for f in r.json()]

    def newversion(self):
        r = requests.post(
            self.zenodo.build_url(self.id, "actions", "newversion"),
            params=self.zenodo.params,
        )
        self.zenodo.check_success(r)
        return ZenodoDeposition(self.zenodo, r.json())

    def latest_draft(self):
        self.data["id"] = self.links["latest_draft"].split("/")[-1]

    def add_file(self, filename, f):
        r = requests.post(
            self.zenodo.build_url(self.id, "files"),
            params=self.zenodo.params,
            data=dict(name=filename),
            files=dict(file=f),
        )
        self.zenodo.check_success(r)

    def update_metadata(self, metadata):
        if isinstance(metadata, ZenodoMetadata):
            metadata = metadata.data
        r = requests.put(
            self.zenodo.build_url(self.id),
            params=self.zenodo.params,
            json={"metadata": metadata},
        )
        self.zenodo.check_success(r)

    def publish(self):
        r = requests.post(
            self.zenodo.build_url(self.id, "actions", "publish"),
            params=self.zenodo.params,
        )
        self.zenodo.check_success(r)


class ZenodoMetadata(AttrDict):
    pass


class ZenodoFile(AttrDict):
    def __init__(self, deposition, *args, **kwargs):
        self.deposition = deposition
        super().__init__(*args, **kwargs)

    def delete(self):
        r = requests.delete(
            self.deposition.zenodo.build_url(self.deposition.id, "files", self.id),
            params=self.deposition.zenodo.params,
        )
        self.deposition.zenodo.check_success(r)
