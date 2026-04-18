FROM oven/bun:1.3.9

WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .

ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ARG VITE_API_KEY=dev-api-key

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_KEY=${VITE_API_KEY}

RUN bun run build

EXPOSE 4173

CMD ["bunx", "--bun", "vite", "preview", "--host", "0.0.0.0", "--port", "4173"]
