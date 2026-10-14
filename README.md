# SBP - Simple Blogging Tool

SBP is a simple tool to serve git repositories as blogs. It can automatically update the posts on push to the main branch and it keeps metada infos about the posts in a simple sqlite3 database that is automatically pushed to the repository when the server syncs with the repository.

## Stack

- Python '>=3.14'
- `uv`
- FastAPI
- SqlAlchemy
- SQLite3

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd sbp
uv sync
```

### 2. Setup config files

Create .secrets.toml in the root directory

```toml
[api]
token="your-super-secret-token"

[repository]
url="git@github.com:user/repository.git"
```

### 3. Setup your ssh keys

SBP only works with ssh origin so you need to configure your ssh keys properly in your system.

### 4. Init and Start

In the root directory run the following commands

```sh
uv run init # <- this will clone the target repository, create the database and make the first push to the repository
uv run server # <- this will start the application on the port 8080 by default
```

now you can access your blog in:

```
http://localhost:8080
```

and to access your posts:

```
http://localhost:8080/path/to/your/post
```

## The blog repository

You need to configure the target repository properly, so here is the required structure:

```
.
├── public
│   └── topic
│       └── post.md
├── README.md *
├── static
│   ├── styles.css
│   └── scripts.js
└── templates
    ├── base.jinja
    ├── index.jinja *
    └── post.jinja *
```

The public folder will hold all your posts, the file of this subfolder will be served "as-is", so you can use the directory structure to organize your publications.

The README.md file is mandatory, it will be served as the home content of your blog.

In the static folder you can put your javascript, css and images that are going to be used, and in the templates folders you are going the jinja templates that will be used to render along with your posts, so you can make it look however you want. The `post.jinja` and `index.jinja` files are mandatory.

Here is an example of the `post.jinja` file:

```jinja
{% extends "base.jinja" %}

{% block title %}{{ post.title }}{% endblock %}

{% block content %}
{{ post.body | markdown | safe }}
<hr class="large" />
{{ post.created_by }}
{{ post.created_at.strftime('%d/%m/%Y') }}
{% endblock %}
```

The filetree is made available to the jinja template with the following format:

```json
{
  "type": "directory",
  "name": "public",
  "children": [
    {
      "type": "directory",
      "name": "topic",
      "children": [{ "type": "file", "path": "topic/post" }]
    }
  ]
}
```

and you can use it in the jinja template with `{{ tree }}`

### 1. Actions

To enable automatic syncronization of your blog you need to configure a workflow to call the /api/sync endpoint in your server:

```yaml
name: Update Blog

on:
  push:
    branches:
      - master
    paths-ignore:
      - 'db.sqlite'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Sync
        run: |
          curl --fail --silent --show-error \
            -X POST 'https://your-domain.com/api/sync' \
            -H "X-Api-Token: ${{ secrets.API_TOKEN }}"
```

!!!! *DO NOT FORGET TO IGNORE THE `db.sqlite` FILE*, this prevents an infinite loop of calling back on your server.