# PaperRec

This project aims to build an automatic AI paper collection and recommendation tool.


# Setup

This project use `poetry` to manage Python dependencies. Make sure you have installed it.

If you use Nix, then just run `nix develop` for a startup.

> This project was only tested in Nix environment. Please report any issues in setup.

Copy the `.env.example` to `.env`, and modify the content in it. Remember to enable the SMTP service of your email provider.

You need docker installed to run the postgresql container. Run `docker compose -f scripts/compose.yaml up -d` to setup the database service.

Run `poetry install && poetry run prisma db push` to setup the Python environment.

> For now, the application can not be ran in docker. We may fix it in the future.

Start the application by running `poetry run paperrec`.

