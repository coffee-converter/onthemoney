# BFF (NestJS) container. Build from apps/api as the context:
#   docker build -f apps/api/Dockerfile -t otm-bff apps/api
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist
# PORT is injected by the host (Fly/Railway); falls back to 3001 in main.ts.
EXPOSE 3001
CMD ["node", "dist/main.js"]
