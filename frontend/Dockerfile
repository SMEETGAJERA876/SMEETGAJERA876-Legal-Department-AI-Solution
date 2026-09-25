# ClauseLens website (Next.js standalone server).
# NEXT_PUBLIC_* values are compiled into the browser code, so they are build arguments.

FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY scripts ./scripts
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AUTH_MODE=firebase
ARG NEXT_PUBLIC_FIREBASE_API_KEY
ARG NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
ARG NEXT_PUBLIC_FIREBASE_PROJECT_ID
ARG NEXT_PUBLIC_FIREBASE_APP_ID
RUN npm run build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
RUN useradd --system --uid 1001 web
COPY --from=build --chown=web /app/.next/standalone ./
COPY --from=build --chown=web /app/.next/static ./.next/static
COPY --from=build --chown=web /app/public ./public
USER web
EXPOSE 3000
CMD ["node", "server.js"]
