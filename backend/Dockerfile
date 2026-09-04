FROM python:3.12-slim

# pdflatex (resume/report PDF rendering) + pdftoppm (PDF preview thumbnails).
# texlive-latex-extra/pictures cover hyperref, xcolor, tikz, longtable, booktabs;
# texlive-fonts-recommended + fonts-recommended cover every font in FONTS
# (lmodern, times, mathpazo, charter, bookman, newcent, helvet, avant).
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-pictures \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# DB_PATH (set via env/compose) should point inside this directory, which is
# volume-mounted for persistence — the config.py default resolves to a path
# outside the image root and won't work here.
RUN mkdir -p /app/data

RUN useradd --create-home appuser && chown -R appuser /app/data
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
