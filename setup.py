import setuptools

VERSION = "0.0.2"

setuptools.setup(
    name="ladderinfo",
    packages=setuptools.find_packages(),
    package_data={"ladderinfo": ["templates/*", "static/styles/*", "static/images/*"]},
    version=VERSION,
    description="Ladder Info app for All Inspiration Apps",
    author="Hugo Wainwright",
    author_email="wainwrighthugo@gmail.com",
    url="https://github.com/frugs/allin-ladderinfo",
    keywords=["sc2", "all-inspiration"],
    classifiers=[],
    install_requires=[
        "requests>=2.19.1",
        "requests-toolbelt>=0.8.0",
        "flask",
        "pyrebase",
        "google-cloud-datastore",
        "sc2gamedata"
    ],
)
