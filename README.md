# Sharepoint Utils

This repository contains utility files that help in scraping data from SharePoint, as downloading files from it at the moment is quite painful.

## Requirements
You only need to have docker and docker-compose installed to run the scripts, although you should be able to run it without docker-compose as well. And to authenticate with SharePoint you only need a single cookie named FedAuth, you can easily obtain this by going to Applications > Cookies and looking for "FedAuth".


The following commands are supported at the moment:

## Flatten
This script explores the entire sharepoint directory and captures all the links recursively in a json file. This script works by scraping the web app using Chrome and Selenium from Python. You can run this script as indicated below:

```bash
docker compose run --rm sharepoint-utils flatten <SharePoint URL> <FedAuth cookie> --debug
```

The `--debug` flag is not required but is very helpful as it takes regular screenshots of the browser while

## Download
This script downloads all the files found by the flatten script and stores things in the directory structure as observed in sharepoint. This script works by downloading all of the files as paraallely as permissible by the resources available using asynchronous requests. You can run this script as indicated below:

```bash
docker compose run --rm sharepoint-utils download <Filename of Flattened JSON with extension> <FedAuth cookie>
```