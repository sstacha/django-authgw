import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(name='django-authgw',
      version='1.0',
      description='Authentication gateway application for the Django framework',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='http://github.com/sstacha/django-authgw',
      author='Steve Stacha',
      author_email='sstacha@gmail.com',
      license='MIT',
      packages=setuptools.find_packages(exclude=["testapp"]),
      include_package_data=True,
      zip_safe=False,
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Framework :: Django :: 3.0",
        "Framework :: Django :: 4.0",
        "Topic :: System :: Systems Administration :: Authentication/Directory",
        "Topic :: Internet :: WWW/HTTP :: Site Management",
        "Topic :: Utilities",
      ],
      python_requires='>=3.8',
      install_requires=[
          'django',
          'ldap3',
      ],
)
