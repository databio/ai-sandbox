---
name: analysis-results-viewer
description: Scaffold an Astro-based results viewer site into an analysis project. Creates a gallery-style web interface that auto-discovers plots and HTML reports from configured folders. Use when you want a browsable web interface for analysis outputs.
---

# Analysis Results Viewer

Add an Astro static site to an analysis project that provides a browsable gallery of plots and reports.

## What This Creates

A `site/` directory in the project root containing a self-contained Astro app:

```
site/
├── package.json
├── astro.config.mjs
├── Dockerfile
├── nginx.conf
├── .gitignore
├── scripts/
│   └── setup-galleries.js     # Creates symlinks from galleries.yaml
├── src/
│   ├── config/
│   │   └── galleries.yaml     # MAIN CONFIG: define galleries here
│   ├── lib/
│   │   └── galleries.js       # Gallery discovery logic
│   ├── layouts/
│   │   └── Layout.astro       # Base layout with nav
│   ├── pages/
│   │   ├── index.astro        # Landing page
│   │   ├── galleries.astro    # Gallery list
│   │   ├── gallery/
│   │   │   └── [id].astro     # Individual gallery view
│   │   └── docs/
│   │       └── [slug].astro   # Markdown doc renderer
│   └── docs/                  # Project documentation (add .md files here)
└── public/
    └── favicon.svg
```

## Steps

### 1. Ask the user for:
- **Project name** (for page titles)
- **Gallery definitions** — folders of results to display. Each needs:
  - An ID (snake_case, e.g., `umap_plots`)
  - A folder path (absolute path or relative to project, may be on another filesystem)
  - A description
- If no galleries specified yet, default to the project's `output/plots/` folder

### 2. Create the site/ directory structure

Create all directories:
```bash
mkdir -p site/scripts site/src/config site/src/lib site/src/layouts site/src/pages/gallery site/src/pages/docs site/src/docs site/public
```

### 3. Write package.json

```json
{
  "name": "[project-name]-results",
  "type": "module",
  "version": "0.0.1",
  "scripts": {
    "predev": "node scripts/setup-galleries.js",
    "dev": "astro dev",
    "prebuild": "node scripts/setup-galleries.js",
    "build": "astro build",
    "preview": "astro preview",
    "setup-galleries": "node scripts/setup-galleries.js"
  },
  "dependencies": {
    "astro": "^5.13.2",
    "js-yaml": "^4.1.0"
  }
}
```

### 4. Write astro.config.mjs

```javascript
// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'http://localhost:4321',
  base: '/',
  build: { assets: 'assets' },
  vite: { ssr: { external: ['fs', 'path'] } }
});
```

### 5. Write galleries.yaml

This is the main configuration file. Each gallery points to a folder of images/reports:

```yaml
galleries:
  results_plots:
    folder_path: ../output/plots
    local_path: results_plots
    description: Analysis result plots
```

Use the gallery definitions from step 1. `folder_path` can be absolute or relative to `site/`. `local_path` is the symlink name in `public/galleries/`.

### 6. Write scripts/setup-galleries.js

```javascript
import { readFileSync, mkdirSync, symlinkSync, readlinkSync, existsSync, lstatSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import yaml from 'js-yaml';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');
const publicDir = resolve(projectRoot, 'public', 'galleries');
const configPath = resolve(projectRoot, 'src', 'config', 'galleries.yaml');

const config = yaml.load(readFileSync(configPath, 'utf8'));

mkdirSync(publicDir, { recursive: true });

for (const [id, gallery] of Object.entries(config.galleries)) {
  const target = resolve(projectRoot, gallery.folder_path);
  const link = resolve(publicDir, gallery.local_path || id);

  if (existsSync(link)) {
    if (lstatSync(link).isSymbolicLink()) {
      const current = readlinkSync(link);
      if (current === target) {
        console.log(`  ✓ ${id}: symlink already correct`);
        continue;
      }
    }
    console.log(`  ✗ ${id}: path exists but is not correct symlink, skipping`);
    continue;
  }

  if (!existsSync(target)) {
    console.log(`  ⚠ ${id}: source path does not exist: ${target}`);
    continue;
  }

  symlinkSync(target, link);
  console.log(`  ✓ ${id}: created symlink → ${target}`);
}
```

### 7. Write src/lib/galleries.js

```javascript
import { readFileSync, readdirSync, statSync, existsSync } from 'fs';
import { resolve, join, dirname, extname } from 'path';
import { fileURLToPath } from 'url';
import yaml from 'js-yaml';

const __dirname = dirname(fileURLToPath(import.meta.url));
const configPath = resolve(__dirname, '..', 'config', 'galleries.yaml');
const publicGalleries = resolve(__dirname, '..', '..', 'public', 'galleries');

function toTitle(id) {
  return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export function getGalleries() {
  const config = yaml.load(readFileSync(configPath, 'utf8'));
  const galleries = {};

  for (const [id, gallery] of Object.entries(config.galleries)) {
    const localDir = resolve(publicGalleries, gallery.local_path || id);
    galleries[id] = {
      id,
      title: toTitle(id),
      description: gallery.description || '',
      folder_path: gallery.folder_path,
      local_path: gallery.local_path || id,
      exists: existsSync(localDir)
    };
  }
  return galleries;
}

export function getGalleryImages(galleryId) {
  const galleries = getGalleries();
  const gallery = galleries[galleryId];
  if (!gallery || !gallery.exists) return [];

  const dir = resolve(publicGalleries, gallery.local_path);
  const extensions = ['.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp'];

  try {
    return readdirSync(dir)
      .filter(f => extensions.includes(extname(f).toLowerCase()))
      .map(f => {
        const filepath = join(dir, f);
        const stats = statSync(filepath);
        return {
          filename: f,
          path: `/galleries/${gallery.local_path}/${f}`,
          lastModified: stats.mtime,
          size: stats.size
        };
      })
      .sort((a, b) => b.lastModified - a.lastModified);
  } catch { return []; }
}

export function getGalleryHtmlFiles(galleryId) {
  const galleries = getGalleries();
  const gallery = galleries[galleryId];
  if (!gallery || !gallery.exists) return [];

  const dir = resolve(publicGalleries, gallery.local_path);

  try {
    return readdirSync(dir)
      .filter(f => extname(f).toLowerCase() === '.html')
      .map(f => {
        const filepath = join(dir, f);
        const stats = statSync(filepath);
        return {
          filename: f,
          path: `/galleries/${gallery.local_path}/${f}`,
          title: f.replace('.html', '').replace(/[_-]/g, ' '),
          lastModified: stats.mtime
        };
      })
      .sort((a, b) => b.lastModified - a.lastModified);
  } catch { return []; }
}
```

### 8. Write src/layouts/Layout.astro

```astro
---
interface Props {
  title: string;
}
const { title } = Astro.props;
---
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    :root {
      --bg: #0f172a; --surface: #1e293b; --border: #334155;
      --text: #e2e8f0; --text-dim: #94a3b8; --accent: #38bdf8;
      --accent-hover: #7dd3fc;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
    nav { background: var(--surface); border-bottom: 1px solid var(--border); padding: 1rem 2rem; display: flex; align-items: center; gap: 2rem; }
    nav a { color: var(--text-dim); text-decoration: none; font-size: 0.9rem; }
    nav a:hover { color: var(--accent); }
    nav .brand { color: var(--text); font-weight: 600; font-size: 1.1rem; }
    main { max-width: 1200px; margin: 0 auto; padding: 2rem; }
    a { color: var(--accent); }
    a:hover { color: var(--accent-hover); }
  </style>
</head>
<body>
  <nav>
    <a href="/" class="brand">TITLE_PLACEHOLDER</a>
    <a href="/">Home</a>
    <a href="/galleries">Galleries</a>
  </nav>
  <main>
    <slot />
  </main>
</body>
</html>
```

Replace `TITLE_PLACEHOLDER` with the project name.

### 9. Write src/pages/index.astro

```astro
---
import Layout from '../layouts/Layout.astro';
import { getGalleries } from '../lib/galleries.js';

const galleries = getGalleries();

// Auto-discover docs
let mdFiles = [];
try {
  const docs = import.meta.glob('../docs/*.md', { eager: true });
  mdFiles = Object.entries(docs).map(([path, mod]) => ({
    slug: path.split('/').pop().replace('.md', ''),
    title: path.split('/').pop().replace('.md', '').replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
  }));
} catch {}
---
<Layout title="TITLE_PLACEHOLDER">
  <h1>TITLE_PLACEHOLDER</h1>

  {mdFiles.length > 0 && (
    <>
      <h2>Documentation</h2>
      <ul>
        {mdFiles.map(doc => (
          <li><a href={`/docs/${doc.slug}`}>{doc.title}</a></li>
        ))}
      </ul>
    </>
  )}

  <h2 style="margin-top: 2rem;">Result Galleries</h2>
  <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; margin-top: 1rem;">
    {Object.entries(galleries).map(([id, gallery]) => (
      <a href={`/gallery/${id}`} style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; text-decoration: none; transition: border-color 0.2s;">
        <h3 style="color: var(--accent); margin-bottom: 0.5rem;">{gallery.title}</h3>
        <p style="color: var(--text-dim); font-size: 0.9rem;">{gallery.description}</p>
        {!gallery.exists && <p style="color: #f87171; font-size: 0.8rem; margin-top: 0.5rem;">⚠ Gallery path not found</p>}
      </a>
    ))}
  </div>
</Layout>
```

Replace `TITLE_PLACEHOLDER` with the project name.

### 10. Write src/pages/galleries.astro

```astro
---
import Layout from '../layouts/Layout.astro';
import { getGalleries, getGalleryImages, getGalleryHtmlFiles } from '../lib/galleries.js';

const galleries = getGalleries();
const galleriesWithCounts = Object.entries(galleries).map(([id, gallery]) => {
  const images = getGalleryImages(id);
  const htmlFiles = getGalleryHtmlFiles(id);
  return { id, ...gallery, imageCount: images.length, htmlCount: htmlFiles.length };
});
---
<Layout title="All Galleries">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
    <h1>All Galleries</h1>
  </div>
  <div style="display: grid; gap: 1rem;">
    {galleriesWithCounts.map(gallery => (
      <a href={`/gallery/${gallery.id}`} style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; text-decoration: none; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h3 style="color: var(--accent);">{gallery.title}</h3>
          <p style="color: var(--text-dim); font-size: 0.9rem;">{gallery.description}</p>
        </div>
        <div style="color: var(--text-dim); font-size: 0.85rem; text-align: right; white-space: nowrap; margin-left: 2rem;">
          {gallery.imageCount > 0 && <div>{gallery.imageCount} images</div>}
          {gallery.htmlCount > 0 && <div>{gallery.htmlCount} reports</div>}
          {!gallery.exists && <div style="color: #f87171;">Not found</div>}
        </div>
      </a>
    ))}
  </div>
</Layout>
```

### 11. Write src/pages/gallery/[id].astro

```astro
---
import Layout from '../../layouts/Layout.astro';
import { getGalleries, getGalleryImages, getGalleryHtmlFiles } from '../../lib/galleries.js';

export function getStaticPaths() {
  const galleries = getGalleries();
  return Object.keys(galleries).map(id => ({ params: { id } }));
}

const { id } = Astro.params;
const galleries = getGalleries();
const gallery = galleries[id];
const images = getGalleryImages(id);
const htmlFiles = getGalleryHtmlFiles(id);
---
<Layout title={gallery?.title || id}>
  <div style="margin-bottom: 2rem;">
    <a href="/galleries" style="color: var(--text-dim); font-size: 0.9rem;">← All Galleries</a>
    <h1 style="margin-top: 0.5rem;">{gallery?.title || id}</h1>
    {gallery?.description && <p style="color: var(--text-dim);">{gallery.description}</p>}
    <p style="color: var(--text-dim); font-size: 0.85rem; margin-top: 0.5rem;">{images.length} images{htmlFiles.length > 0 ? `, ${htmlFiles.length} reports` : ''}</p>
  </div>

  {htmlFiles.length > 0 && (
    <div style="margin-bottom: 2rem;">
      <h2>Reports</h2>
      <div style="display: grid; gap: 0.5rem; margin-top: 1rem;">
        {htmlFiles.map(f => (
          <a href={f.path} target="_blank" style="background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 0.75rem 1rem; text-decoration: none; display: flex; justify-content: space-between; align-items: center;">
            <span style="color: var(--accent);">{f.title}</span>
            <span style="color: var(--text-dim); font-size: 0.8rem;">{f.lastModified.toLocaleDateString()}</span>
          </a>
        ))}
      </div>
    </div>
  )}

  {images.length > 0 && (
    <>
      <h2>Images</h2>
      <div class="image-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; margin-top: 1rem;">
        {images.map(img => (
          <div class="image-card" data-src={img.path} style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; cursor: pointer;">
            <img src={img.path} alt={img.filename} loading="lazy" style="width: 100%; display: block;" />
            <div style="padding: 0.5rem 0.75rem;">
              <div style="color: var(--text); font-size: 0.8rem; word-break: break-all;">{img.filename}</div>
              <div style="color: var(--text-dim); font-size: 0.75rem;">{img.lastModified.toLocaleDateString()}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  )}

  <!-- Modal for full-size images -->
  <div id="modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.9); z-index:100; cursor:pointer; justify-content:center; align-items:center;">
    <img id="modal-img" style="max-width:95vw; max-height:95vh; object-fit:contain;" />
  </div>

  <script>
    document.querySelectorAll('.image-card').forEach(card => {
      card.addEventListener('click', () => {
        const src = card.dataset.src;
        const modal = document.getElementById('modal');
        const img = document.getElementById('modal-img');
        img.src = src;
        modal.style.display = 'flex';
      });
    });
    document.getElementById('modal').addEventListener('click', () => {
      document.getElementById('modal').style.display = 'none';
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') document.getElementById('modal').style.display = 'none';
    });
  </script>
</Layout>
```

### 12. Write src/pages/docs/[slug].astro

```astro
---
import Layout from '../../layouts/Layout.astro';

export async function getStaticPaths() {
  const docs = import.meta.glob('../../docs/*.md', { eager: true });
  return Object.entries(docs).map(([path, mod]) => ({
    params: { slug: path.split('/').pop().replace('.md', '') },
    props: { content: mod.compiledContent(), title: path.split('/').pop().replace('.md', '').replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }
  }));
}

const { content, title } = Astro.props;
---
<Layout title={title}>
  <a href="/" style="color: var(--text-dim); font-size: 0.9rem;">← Home</a>
  <article style="margin-top: 1rem; line-height: 1.7;">
    <h1>{title}</h1>
    <Fragment set:html={content} />
  </article>
</Layout>
```

### 13. Write .gitignore for site/

```gitignore
node_modules/
dist/
.astro/
public/galleries/
```

### 14. Write Dockerfile and nginx.conf

**Dockerfile:**
```dockerfile
FROM node:24-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**nginx.conf:**
```nginx
server {
    listen 80;
    absolute_redirect off;
    port_in_redirect off;
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
        rewrite ^([^.]*[^/])$ $1/ permanent;
    }
}
```

### 15. Final instructions to user

After scaffolding:
```bash
cd site && npm install && npm run dev
```

To add galleries later, edit `site/src/config/galleries.yaml` and restart.
To add documentation, add `.md` files to `site/src/docs/`.

## Important

- Replace ALL occurrences of `TITLE_PLACEHOLDER` with the actual project name
- The `galleries.yaml` is the primary configuration — everything else is generic
- If `output/plots/` is a symlink or on another filesystem, use the absolute path in `folder_path`
- The site auto-discovers images (PNG, JPG, SVG, GIF, WebP) and HTML reports in each gallery folder
