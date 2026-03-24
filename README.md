# Stock Portfolio Optimizer

This project uses [Django Tailwind](https://django-tailwind.readthedocs.io/) for styling. Before running the server you need to install Node and Python dependencies used by Tailwind.

## Quick setup

Run the helper script to install everything and build the CSS once:

```bash
./scripts/setup_tailwind.sh
```

After running the script you can start the Tailwind watcher during development with:

```bash
python manage.py tailwind start
```

This will rebuild your CSS when you edit files in `theme/static_src`.
