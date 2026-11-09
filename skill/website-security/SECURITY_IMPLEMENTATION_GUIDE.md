# SECURITY_IMPLEMENTATION_GUIDE.md

Practical, copy-adaptable implementation patterns for **Laravel, PHP, Vue/JavaScript, Nginx, Linux and Cloudflare**. Concepts, threat context and rationale are in `WEBSITE_SECURITY_SKILL.md` (section references appear as *Ref*). This file is deliberately recipe-oriented and avoids repeating that reasoning.

> **Read before using any recipe**
> - These are **examples, not universal requirements.** Detect the project's actual stack first; adapt names, versions and paths. Do not install a package or change a server because a recipe mentions it.
> - Examples target **Laravel 11 to 13 and PHP 8.3+**. Where an API differs between versions it is noted; verify against the project's installed version and the official docs (Part 18 of the main document).
> - Never paste secrets into these files. Replace every `<placeholder>` and `example.com`.
> - Every recipe ends with a **Verify** step. A recipe is not done until its verification passes and legitimate functionality still works.

## Contents

1. [Laravel: assembled secure baseline](#1-laravel-assembled-secure-baseline)
2. [Laravel: tenant isolation that fails closed](#2-laravel-tenant-isolation-that-fails-closed)
3. [Laravel: money, ledger and idempotency schema](#3-laravel-money-ledger-and-idempotency-schema)
4. [Laravel: webhook endpoint](#4-laravel-webhook-endpoint)
5. [Laravel: uploads end to end](#5-laravel-uploads-end-to-end)
6. [Laravel: TOTP two-factor enrolment](#6-laravel-totp-two-factor-enrolment)
7. [Plain PHP (no framework) essentials](#7-plain-php-no-framework-essentials)
8. [Vue / JavaScript front end](#8-vue--javascript-front-end)
9. [Nginx and PHP-FPM assembled configuration](#9-nginx-and-php-fpm-assembled-configuration)
10. [Linux host hardening files](#10-linux-host-hardening-files)
11. [Cloudflare: origin lock and rule recipes](#11-cloudflare-origin-lock-and-rule-recipes)
12. [Verification harness (tests and smoke script)](#12-verification-harness-tests-and-smoke-script)

---

## 1. Laravel: assembled secure baseline

*Ref: 4.9, 5.6, 6.2 to 6.6, 14.1.* Bring the individual controls together in `bootstrap/app.php` (Laravel 11+ style). Keep what the project already has; merge rather than replace.

```php
<?php
// bootstrap/app.php
use App\Http\Middleware\ApiRequestHygiene;
use App\Http\Middleware\EnforceAbsoluteSessionLifetime;
use App\Http\Middleware\SecurityHeaders;
use App\Http\Middleware\VerifyWebhookSignature;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__ . '/../routes/web.php',
        api: __DIR__ . '/../routes/api.php',
        commands: __DIR__ . '/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware) {
        // Reject unexpected Host headers (password-reset poisoning, cache poisoning). Patterns are regexes.
        $middleware->trustHosts(at: [env('APP_TRUSTED_HOST_REGEX', '^example\.com$')]);

        // Prefer restoring the client IP at Nginx (realip). Configure proxies here only if another proxy
        // actually fronts the app, and never use '*' unless the origin accepts traffic solely from that proxy.
        // $middleware->trustProxies(at: ['10.0.0.0/8']);

        $middleware->web(append: [
            SecurityHeaders::class,
            EnforceAbsoluteSessionLifetime::class . ':720',     // absolute lifetime in minutes (staff apps)
        ]);

        $middleware->api(append: [ApiRequestHygiene::class]);

        $middleware->alias([
            'verify.webhook' => VerifyWebhookSignature::class,
            'abilities'      => \Laravel\Sanctum\Http\Middleware\CheckAbilities::class,
            'ability'        => \Laravel\Sanctum\Http\Middleware\CheckForAnyAbility::class,
        ]);

        // CSRF/request-forgery exclusions: ONLY signature-verified machine endpoints, never user-facing routes.
        // Laravel 11/12: $middleware->validateCsrfTokens(except: ['webhooks/*']);
        // Laravel 13: $middleware->preventRequestForgery(except: ['webhooks/*']);   (validateCsrfTokens() still works and delegates)
    })
    ->withExceptions(function (Exceptions $exceptions) {
        $exceptions->shouldRenderJsonWhen(fn (Request $request, Throwable $e) => $request->is('api/*') || $request->expectsJson());
        $exceptions->dontFlash(['current_password', 'password', 'password_confirmation', 'otp', 'token']);
    })
    ->create();
```

`AppServiceProvider::boot()` (strict models, forced URL root, rate limiters):

```php
<?php
namespace App\Providers;

use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\Facades\URL;
use Illuminate\Support\Str;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function boot(): void
    {
        Model::shouldBeStrict(! $this->app->isProduction());

        if ($this->app->isProduction()) {
            URL::forceScheme('https');
            URL::forceRootUrl((string) config('app.url'));           // never build links from the request Host
        }

        RateLimiter::for('login', fn (Request $r) => [
            Limit::perMinute(5)->by(Str::lower((string) $r->input('email')) . '|' . $r->ip()),
            Limit::perMinute(30)->by($r->ip()),
        ]);

        RateLimiter::for('api', fn (Request $r) => $r->user()
            ? Limit::perMinute(120)->by('u:' . $r->user()->id)
            : Limit::perMinute(30)->by('ip:' . $r->ip()));

        RateLimiter::for('api-sensitive', fn (Request $r) => [
            Limit::perMinute(10)->by('u:' . ($r->user()?->id ?? 'guest') . '|' . $r->ip()),
            Limit::perDay(200)->by('u:' . ($r->user()?->id ?? 'guest')),
        ]);

        RateLimiter::for('webhooks', fn (Request $r) => Limit::perMinute(300)->by($r->ip()));
    }
}
```

**Verify:** `php artisan about` shows production/debug off; header test (12.1); forged `Host` request returns 400; 6th failed login returns 429; `php artisan route:list` shows `throttle` on auth routes.

## 2. Laravel: tenant isolation that fails closed

*Ref: C.1, AZ-02/AZ-03.* A global scope that silently does nothing when no user is present **fails open** (queue jobs, console commands, mis-ordered middleware). Make "no tenant context" return nothing unless a trusted code path sets one.

```php
<?php
namespace App\Support;

/** Request/job-scoped tenant context. Set by middleware after authentication, or explicitly by trusted jobs. */
final class TenantContext
{
    private ?int $companyId = null;

    public function set(?int $companyId): void { $this->companyId = $companyId; }
    public function id(): ?int { return $this->companyId; }
}
// Register as a scoped singleton: $this->app->scoped(TenantContext::class);
```

```php
<?php
namespace App\Models\Concerns;

use App\Support\TenantContext;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;

trait BelongsToCompany
{
    protected static function bootBelongsToCompany(): void
    {
        static::addGlobalScope('company', function (Builder $query) {
            $companyId = app(TenantContext::class)->id();
            $table = $query->getModel()->getTable();

            if ($companyId === null) {
                $query->whereRaw('1 = 0');                         // FAIL CLOSED: no context, no rows
                return;
            }
            $query->where($table . '.company_id', $companyId);
        });

        static::creating(function (Model $model) {
            $companyId = app(TenantContext::class)->id();
            if ($companyId === null) {
                throw new \LogicException('Cannot create a tenant-owned record without tenant context');
            }
            $model->company_id = $companyId;                       // never taken from request input
        });
    }
}
```

```php
<?php
namespace App\Http\Middleware;

use App\Support\TenantContext;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

final class SetTenantContext
{
    public function handle(Request $request, Closure $next): Response
    {
        app(TenantContext::class)->set($request->user()?->company_id);   // after authentication middleware
        return $next($request);
    }
}
// Queue jobs that act for a tenant: pass company_id in the job and call TenantContext::set() in handle().
// Cross-tenant admin tooling must call ->withoutGlobalScope('company') explicitly and be audited.
```

**Verify:** a Pest test that creates records for two companies, authenticates as one, and asserts reads/updates/deletes/exports of the other return nothing/404; a console-context test asserting the scoped query returns zero rows.

## 3. Laravel: money, ledger and idempotency schema

*Ref: H.1 to H.3, 7.1.* Database constraints are the real guard; application code can have bugs and races.

```php
<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('wallets', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->restrictOnDelete();
            $table->char('currency', 3);
            $table->bigInteger('balance_minor')->default(0);           // integer minor units, never float
            $table->timestamps();
            $table->unique(['user_id', 'currency']);
        });
        // CHECK constraints are enforced by MySQL 8.0.16+ and MariaDB 10.2+; verify on your engine/version.
        DB::statement('ALTER TABLE wallets ADD CONSTRAINT wallets_balance_non_negative CHECK (balance_minor >= 0)');

        Schema::create('ledger_entries', function (Blueprint $table) {
            $table->id();
            $table->foreignId('wallet_id')->constrained()->restrictOnDelete();
            $table->bigInteger('amount_minor');                        // signed; corrections are NEW rows
            $table->string('reference', 64)->unique();                 // idempotent posting key
            $table->string('kind', 32);
            $table->foreignId('actor_id')->nullable()->constrained('users')->nullOnDelete();
            $table->timestamp('created_at')->useCurrent();
        });

        // Append-only enforcement at the database level (MySQL/MariaDB syntax).
        DB::unprepared("CREATE TRIGGER ledger_entries_no_update BEFORE UPDATE ON ledger_entries
            FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ledger_entries is append-only'");
        DB::unprepared("CREATE TRIGGER ledger_entries_no_delete BEFORE DELETE ON ledger_entries
            FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'ledger_entries is append-only'");

        Schema::create('orders', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->restrictOnDelete();
            $table->string('idempotency_key', 64);
            $table->string('status', 24)->default('pending');
            $table->char('currency', 3);
            $table->bigInteger('total_minor')->default(0);
            $table->timestamps();
            $table->unique(['user_id', 'idempotency_key']);            // duplicate submissions collide here
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('orders');
        DB::unprepared('DROP TRIGGER IF EXISTS ledger_entries_no_delete');
        DB::unprepared('DROP TRIGGER IF EXISTS ledger_entries_no_update');
        Schema::dropIfExists('ledger_entries');
        Schema::dropIfExists('wallets');
    }
};
```

Reconciliation job (run on a schedule, alert on any row returned):

```sql
SELECT w.id, w.balance_minor, COALESCE(SUM(l.amount_minor), 0) AS ledger_sum
FROM wallets w
LEFT JOIN ledger_entries l ON l.wallet_id = w.id
GROUP BY w.id, w.balance_minor
HAVING w.balance_minor <> COALESCE(SUM(l.amount_minor), 0);
```

Service patterns (checkout with locking, wallet debit with atomic conditional update) are in the main document H.1 and H.2.

**Verify:** the parallel-request script (main document H.4) shows exactly one success; attempting `UPDATE`/`DELETE` on `ledger_entries` fails; reconciliation returns zero rows.

## 4. Laravel: webhook endpoint

*Ref: D.2, 6.1.* Use the signature middleware from the main document (D.2) and register the route with its own limiter. The route is exempt from CSRF/request-forgery protection **only because** it authenticates by signature.

```php
<?php
// routes/api.php (or routes/web.php with the CSRF exclusion configured for the path)
use App\Http\Controllers\ProviderWebhookController;
use Illuminate\Support\Facades\Route;

Route::post('/webhooks/provider', ProviderWebhookController::class)
    ->middleware(['throttle:webhooks', 'verify.webhook'])
    ->name('webhooks.provider');
```

```php
<?php
namespace App\Http\Controllers;

use App\Jobs\ProcessProviderEvent;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

final class ProviderWebhookController extends Controller
{
    public function __invoke(Request $request): Response
    {
        // Signature, timestamp window and event-ID de-duplication already passed in the middleware.
        $payload = $request->json()->all();

        // Do minimal work inline: validate shape, enqueue, acknowledge. Handlers must be idempotent and must
        // re-fetch authoritative state from the provider where amounts/status matter (never trust the payload alone).
        ProcessProviderEvent::dispatch([
            'id'   => (string) ($payload['id'] ?? ''),
            'type' => (string) ($payload['type'] ?? ''),
        ]);

        return response()->noContent();
    }
}
```

**Verify:** unsigned payload returns 401 and logs a failed-signature event; replaying a signed payload twice processes it once; a payload with an old timestamp is rejected.

## 5. Laravel: uploads end to end

*Ref: F.1 to F.3.* Migration and model for private attachments (the controller and delivery code are in the main document F.1 and F.2).

```php
<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('attachments', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->string('path', 255);                      // server-generated, e.g. avatars/<uuid>.webp
            $table->string('mime', 100);                      // from your allowlist, never from the client
            $table->string('display_name', 120)->nullable();  // sanitised original name, for display only
            $table->unsignedBigInteger('size_bytes')->default(0);
            $table->timestamps();
        });
    }

    public function down(): void { Schema::dropIfExists('attachments'); }
};
```

```php
<?php
// config/filesystems.php (excerpt): a private disk that is NEVER symlinked into public/
return [
    'disks' => [
        'private' => [
            'driver'     => 'local',
            'root'       => storage_path('app/private'),
            'visibility' => 'private',
            'throw'      => true,        // surface storage failures instead of a silent false
        ],
        // ... other disks unchanged
    ],
];
```

**Verify:** upload a renamed script (rejected or re-encoded); download another user's attachment (403/404); response headers include `X-Content-Type-Options: nosniff`; the stored file is not reachable by any public URL.

## 6. Laravel: TOTP two-factor enrolment

*Ref: 5.4.* Prefer the framework's first-party starter kit (Fortify) for production 2FA; this shows the data model and the checks that must exist, using `pragmarx/google2fa`.

```php
<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->text('totp_secret')->nullable();                 // cast 'encrypted' on the model
            $table->unsignedBigInteger('totp_last_step')->nullable();
            $table->timestamp('totp_confirmed_at')->nullable();
        });
        Schema::create('recovery_codes', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->string('code_hash', 255);                        // hashed like a password
            $table->timestamp('used_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('recovery_codes');
        Schema::table('users', fn (Blueprint $table) => $table->dropColumn(['totp_secret', 'totp_last_step', 'totp_confirmed_at']));
    }
};
```

```php
<?php
namespace App\Services;

use App\Models\User;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

final class RecoveryCodes
{
    /** @return list<string> plaintext codes, shown ONCE to the user */
    public function generate(User $user, int $count = 10): array
    {
        $user->recoveryCodes()->delete();
        $plain = [];
        for ($i = 0; $i < $count; $i++) {
            $code = Str::lower(Str::random(5) . '-' . Str::random(5));
            $plain[] = $code;
            $user->recoveryCodes()->create(['code_hash' => Hash::make($code)]);
        }
        return $plain;
    }

    /** Single use; rate-limit callers. */
    public function consume(User $user, string $input): bool
    {
        foreach ($user->recoveryCodes()->whereNull('used_at')->get() as $row) {
            if (Hash::check(Str::lower(trim($input)), $row->code_hash)) {
                $row->forceFill(['used_at' => now()])->save();
                return true;
            }
        }
        return false;
    }
}
```

The verification service is in the main document (5.4). Flow rules: the secret is unusable until the user proves a valid code (`totp_confirmed_at`); "MFA passed" lives in the server-side session with a timestamp for step-up; every MFA route has its own limiter; changing MFA settings requires fresh re-authentication and notifies the user.

**Verify:** replaying the same code in the same time step fails; the 6th wrong code in 5 minutes is throttled; accessing a post-login route after step 1 only redirects to the MFA challenge.

---

## 7. Plain PHP (no framework) essentials

*Ref: Parts 2, 5, 4.* For projects without Laravel. These are minimal, correct building blocks; prefer a maintained framework or library for anything larger.

```php
<?php
declare(strict_types=1);

// --- Database: prepared statements, exceptions on error, no emulated prepares ---
$pdo = new PDO($dsn, $dbUser, $dbPass, [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_EMULATE_PREPARES   => false,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
]);
$stmt = $pdo->prepare('SELECT id, name FROM users WHERE email = :email');
$stmt->execute([':email' => $email]);
$user = $stmt->fetch();

// --- Passwords: Argon2id, rehash when parameters change ---
$options = ['memory_cost' => 65536, 'time_cost' => 4, 'threads' => 1];       // KiB; tune to your hardware
$hash = password_hash($password, PASSWORD_ARGON2ID, $options);
if (password_verify($password, $storedHash)) {
    if (password_needs_rehash($storedHash, PASSWORD_ARGON2ID, $options)) {
        $newHash = password_hash($password, PASSWORD_ARGON2ID, $options);     // persist it
    }
}

// --- Output encoding for HTML text and quoted attributes ---
function e(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// --- Sessions: secure cookie parameters, strict mode, regenerate on login ---
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
session_set_cookie_params([
    'lifetime' => 0, 'path' => '/', 'secure' => true, 'httponly' => true, 'samesite' => 'Lax',
]);
session_start();
// After successful authentication:
session_regenerate_id(true);
$_SESSION['auth_started_at'] = time();

// --- CSRF token (synchroniser token pattern) ---
function csrfToken(): string
{
    return $_SESSION['csrf'] ??= bin2hex(random_bytes(32));
}
function verifyCsrf(?string $submitted): void
{
    if (!is_string($submitted) || !hash_equals($_SESSION['csrf'] ?? '', $submitted)) {
        http_response_code(419);
        exit('Invalid request');
    }
}
// In forms: <input type="hidden" name="_csrf" value="<?= e(csrfToken()) ?>">   Verify on every POST/PUT/DELETE.

// --- Baseline headers (set before any output) ---
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: strict-origin-when-cross-origin');
header('X-Frame-Options: DENY');
header("Content-Security-Policy: default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");

// --- Safe redirect, uploads, throttling: reuse the patterns in the main document (B.5, F.1, C.3).
```

**Verify:** SQL lone-quote test returns no error; a POST without `_csrf` returns 419; session ID changes at login; cookie flags present in `Set-Cookie`.

---

## 8. Vue / JavaScript front end

*Ref: 8.1 to 8.8, 4.2, 5.1.* Examples use Vue 3 + Vite; the principles transfer to React, Angular and vanilla JS.

### 8.1 Project baseline

```ini
# .npmrc
ignore-scripts=true
audit-level=high
```

```javascript
// src/lib/safeUrl.js : the only way user-supplied URLs reach href/src
export function safeUrl(input, allowed = ['https:', 'http:', 'mailto:', 'tel:']) {
  try {
    const url = new URL(String(input), window.location.origin);
    return allowed.includes(url.protocol) ? url.href : '#';
  } catch {
    return '#';
  }
}
```

```vue
<!-- src/components/SafeHtml.vue : the ONLY place v-html is allowed; sanitises immediately before insertion -->
<script setup>
import { computed } from 'vue';
import DOMPurify from 'dompurify';

const props = defineProps({ html: { type: String, required: true } });
const clean = computed(() => DOMPurify.sanitize(props.html, { SANITIZE_NAMED_PROPS: true }));
</script>

<template>
  <div v-html="clean"></div>
</template>
```

Add an ESLint rule or CI grep that fails on `v-html` outside `SafeHtml.vue`:

```bash
# CI guard: any v-html outside the audited component fails the build
if grep -RIn --include='*.vue' --include='*.js' --include='*.ts' 'v-html' src | grep -v 'src/components/SafeHtml.vue'; then
  echo "v-html is only permitted in SafeHtml.vue" >&2
  exit 1
fi
```

### 8.2 API client (cookie session) and safe error handling

```javascript
// src/lib/api.js
import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,            // public value only
  withCredentials: true,                                  // session cookie
  withXSRFToken: true,                                    // send X-XSRF-TOKEN from the XSRF-TOKEN cookie
  headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
  timeout: 15000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    if (status === 401) {
      window.location.assign('/login');                   // session ended: server is the authority
    }
    // Show a generic message plus the server correlation id; never render server bodies as HTML.
    const correlationId = error.response?.data?.instance ?? 'n/a';
    return Promise.reject({ status, message: 'Something went wrong. Please try again.', correlationId });
  },
);

// Before the first state-changing request in a session (Laravel Sanctum SPA mode):
//   await api.get('/sanctum/csrf-cookie');
```

Route guards improve UX only. The API must authorise each call (main document 8.2).

### 8.3 Vite configuration: CSP-friendly build, no public source maps

```javascript
// vite.config.js
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  build: {
    sourcemap: false,            // or 'hidden' and upload the maps privately to your error tracker
  },
  html: {
    // Inserts a nonce placeholder into generated <script>/<style> tags; the server replaces it per response.
    cspNonce: '__CSP_NONCE__',
  },
});
// Only variables prefixed VITE_ reach the browser bundle: never put secrets in them.
```

If the SPA's `index.html` is served by Laravel/Blade, render it through a Blade view so `{{ Vite::cspNonce() }}` supplies a real per-request nonce; if it is a static file behind Nginx/CDN, use hashes or edge nonce injection instead (a cached HTML file cannot carry a per-request nonce).

### 8.4 Secrets and bundle hygiene check

```bash
# After build: fail if obvious secrets or internal hosts ended up in the bundle
npm run build
if grep -RInE '(sk_live_|-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|password\s*[:=]\s*["'\''][^"'\'']+)' dist; then
  echo "Possible secret in build output" >&2; exit 1
fi
gitleaks dir dist --redact --no-banner       # (older gitleaks: gitleaks detect --no-git --source dist)
```

**Verify (front end):** marker string in every user-controlled field renders as text; `javascript:` URL in a profile field becomes `#`; no auth token readable from `localStorage`/`sessionStorage`; CSP violations panel is clean on a production-like build; `npm ci --ignore-scripts && npm audit --omit=dev && npm audit signatures` passes.

---

## 9. Nginx and PHP-FPM assembled configuration

*Ref: 9.5, 9.6, G.1, G.2, 4.10, 3.4.3.* A complete, consistent set. Test with `nginx -t` and keep the old config until the new one is confirmed.

### 9.1 Shared snippets

```nginx
# /etc/nginx/snippets/security-headers.conf  (include in every server/location that sets add_header)
add_header X-Content-Type-Options     "nosniff" always;
add_header Referrer-Policy            "strict-origin-when-cross-origin" always;
add_header Permissions-Policy         "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header X-Frame-Options            "DENY" always;
# CSP and Cache-Control are set by the application (nonces and per-route cache rules).
# HSTS: enable only after the staged ramp (main document 4.3):
# add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

```nginx
# /etc/nginx/conf.d/00-security-global.conf  (http context)
server_tokens off;
client_header_timeout 10s;
client_body_timeout   15s;
send_timeout          15s;
keepalive_timeout     15s;
client_max_body_size  10m;

limit_conn_zone $binary_remote_addr zone=perip:10m;

# Rate-limit only POST /login (empty key means "not limited").
map "$request_method:$uri" $login_key {
    default       "";
    "POST:/login" $binary_remote_addr;
}
limit_req_zone $login_key zone=login:10m rate=5r/m;
limit_req_status 429;
limit_conn_status 429;
```

### 9.2 Catch-all and the application vhost

```nginx
# /etc/nginx/sites-available/00-default-deny.conf : unknown Host or direct-IP requests get nothing
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    ssl_certificate     /etc/ssl/catchall/fullchain.pem;      # any valid (self-signed is fine) certificate
    ssl_certificate_key /etc/ssl/catchall/privkey.pem;
    server_name _;
    return 444;
}
```

```nginx
# /etc/nginx/sites-available/example.conf
server {
    listen 80;
    listen [::]:80;
    server_name example.com;
    location /.well-known/acme-challenge/ { root /var/www/acme; }
    location / { return 301 https://example.com$request_uri; }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;                                          # nginx >= 1.25.1 (older: listen 443 ssl http2;)
    server_name example.com;

    root  /var/www/example/current/public;
    index index.php;

    ssl_certificate     /etc/ssl/example/fullchain.pem;
    ssl_certificate_key /etc/ssl/example/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;               # take the cipher policy from Mozilla's SSL config generator
    ssl_session_timeout 1d;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_tickets off;

    # Cloudflare Authenticated Origin Pulls with YOUR certificate (see section 11); uncomment after setup:
    # ssl_client_certificate /etc/ssl/example/aop-client-ca.pem;
    # ssl_verify_client on;

    include snippets/security-headers.conf;
    limit_conn perip 30;
    limit_req  zone=login burst=5 nodelay;

    location ~ /\.(?!well-known) { deny all; return 404; }
    location ~* \.(sql|bak|old|orig|swp|dist|log|ini|sh|yml|yaml|lock)$ { deny all; return 404; }

    location / {
        try_files $uri $uri/ /index.php?$query_string;
        autoindex off;
    }

    # Immutable fingerprinted assets (Vite output)
    location ^~ /build/ {
        include snippets/security-headers.conf;        # add_header in a nested block REPLACES inherited ones
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        try_files $uri =404;
    }

    location ~ ^/index\.php(/|$) {
        fastcgi_pass unix:/run/php/php8.3-fpm-example.sock;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
        fastcgi_hide_header X-Powered-By;
        fastcgi_read_timeout 60s;
    }
    location ~ \.php$ { return 404; }                  # only the front controller executes
}
```

### 9.3 Admin host with network restriction

```nginx
server {
    listen 443 ssl;
    http2 on;
    server_name admin.example.com;
    ssl_certificate     /etc/ssl/admin/fullchain.pem;
    ssl_certificate_key /etc/ssl/admin/privkey.pem;

    allow 203.0.113.0/24;              # office/VPN egress (replace); everyone else is refused
    deny  all;

    include snippets/security-headers.conf;
    add_header X-Robots-Tag "noindex, nofollow" always;
    # ... same root/fastcgi blocks as the main vhost ...
}
```

Behind Cloudflare, an `allow`/`deny` list sees the restored client IP only after realip is configured on a locked origin (section 11); otherwise prefer Cloudflare Access/Zero Trust for the admin hostname.

### 9.4 PHP-FPM pool

```ini
; /etc/php/8.3/fpm/pool.d/example.conf
[example]
user  = siteuser
group = siteuser
listen = /run/php/php8.3-fpm-example.sock
listen.owner = www-data
listen.group = www-data
listen.mode  = 0660

pm = ondemand
pm.max_children = 20
pm.process_idle_timeout = 20s
pm.max_requests = 500
request_terminate_timeout = 60s

php_admin_value[open_basedir]      = /var/www/example/:/tmp/:/usr/share/php/
php_admin_value[upload_tmp_dir]    = /var/www/example/shared/tmp
php_admin_value[session.save_path] = /var/www/example/shared/sessions
php_admin_flag[log_errors]         = on
php_admin_flag[display_errors]     = off
php_admin_value[error_log]         = /var/log/php/example-error.log
php_admin_value[disable_functions] = exec,passthru,shell_exec,system,popen,pcntl_exec,show_source,highlight_file
```

Test every feature that might spawn a process (PDF generation, image tools, mail via sendmail transport) before keeping `disable_functions`; CLI workers use the CLI `php.ini` and are unaffected.

**Verify:** `nginx -t && php-fpm8.3 -t`; request an uploaded `.php`-named file (404); `curl -I https://example.com/.env` (404); `curl -sk --resolve example.com:443:<origin-ip> https://example.com/` from outside Cloudflare fails once origin lock is on; headers present on `/`, a 404 and a static asset.

---

## 10. Linux host hardening files

*Ref: 9.1 to 9.8.* Apply on Ubuntu LTS with root access **and an out-of-band console**. Validate each change before applying and keep an existing SSH session open while testing a new one.

### 10.1 sysctl

```ini
# /etc/sysctl.d/99-hardening.conf   (apply: sysctl --system)
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.conf.all.log_martians = 1
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
```

### 10.2 fail2ban

```ini
# /etc/fail2ban/jail.d/local.conf
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8 ::1 203.0.113.0/24      ; your admin/VPN range (replace)

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-botsearch]
enabled = true
logpath = /var/log/nginx/access.log

[nginx-limit-req]
enabled = true
logpath = /var/log/nginx/error.log
```

Behind a CDN the banned address must be the **real** client IP (realip configured on a locked origin), otherwise you may ban the CDN and take the site down. Prefer edge-level blocking for web abuse and keep fail2ban focused on SSH and direct-origin probes. Test with `fail2ban-client status <jail>` and a deliberate failed login from a test IP.

### 10.3 Queue worker under systemd (hardened)

```ini
# /etc/systemd/system/example-queue.service
[Unit]
Description=Laravel queue worker (example)
After=network.target

[Service]
User=siteuser
Group=siteuser
WorkingDirectory=/var/www/example/current
ExecStart=/usr/bin/php artisan queue:work --sleep=3 --tries=3 --max-time=3600 --memory=256
Restart=always
RestartSec=5
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes                       ; if the site lives under /home (for example CloudPanel), use read-only/ReadWritePaths instead
ReadWritePaths=/var/www/example/shared/storage /var/www/example/current/bootstrap/cache
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
LockPersonality=yes
CapabilityBoundingSet=
AmbientCapabilities=

[Install]
WantedBy=multi-user.target
```

Run `systemctl daemon-reload && systemctl enable --now example-queue`. After each deploy: `php artisan queue:restart`. Check with `systemd-analyze security example-queue`.

### 10.4 Unattended security updates, log rotation, scheduler

```ini
# /etc/apt/apt.conf.d/20auto-upgrades
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```

```text
# /etc/logrotate.d/example-laravel
/var/www/example/shared/storage/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 siteuser adm
    su siteuser siteuser
}
```

```text
# crontab -u siteuser -e   (scheduler: absolute paths, no secrets on the command line, overlap protection in the app)
* * * * * cd /var/www/example/current && /usr/bin/php artisan schedule:run >> /dev/null 2>&1
```

### 10.5 SSH and firewall

Use the files and commands in the main document 9.3 and 9.4 (SSH drop-in, `sshd -t` before reload, UFW default-deny, SSH limited to admin networks, database ports private).

**Verify:** `sysctl net.ipv4.tcp_syncookies`; `sshd -T | grep -Ei 'permitrootlogin|passwordauthentication'`; `ufw status verbose`; external port scan of your own host shows only 80/443 (and SSH from allowed networks); `systemctl status example-queue`; `unattended-upgrade --dry-run` succeeds.

---

## 11. Cloudflare: origin lock and rule recipes

*Ref: Part 3.* Dashboard names and plan limits change: confirm against the Cloudflare documentation (main document Part 18) before relying on this section.

### 11.1 Order of operations (do not skip the middle steps)

1. Proxy the hostnames (orange cloud); set SSL/TLS to **Full (strict)** with a valid origin certificate (Cloudflare Origin CA certificate or a public CA certificate installed at the origin).
2. Add a **custom WAF rule** set and **rate limit** for login/reset/OTP (11.3), in log/challenge mode first where available.
3. **Lock the origin** (11.2).
4. Only now restore real client IPs at the origin with `realip` (main document 3.4.2).
5. Enable DNSSEC (add the DS record at the registrar), add CAA records, enable security notifications, and protect the Cloudflare account (security-key MFA, scoped API tokens).
6. Verify by direct-origin test (11.4), then raise HSTS through the staged ramp.

### 11.2 Origin lock options

**Option A: Cloudflare Tunnel (strongest).** No inbound web ports at all.

```bash
# On the origin host (install cloudflared from Cloudflare's official package repository first)
cloudflared tunnel login
cloudflared tunnel create example-origin
cloudflared tunnel route dns example-origin example.com
```

```yaml
# /etc/cloudflared/config.yml
tunnel: <TUNNEL-UUID>
credentials-file: /etc/cloudflared/<TUNNEL-UUID>.json
ingress:
  - hostname: example.com
    service: http://127.0.0.1:8080       # Nginx listening on loopback only
  - service: http_status:404
```

```bash
cloudflared service install
systemctl enable --now cloudflared
# Then: Nginx `listen 127.0.0.1:8080;`, firewall closes 80/443 to the world, realip trusts only 127.0.0.1:
#   set_real_ip_from 127.0.0.1;  real_ip_header CF-Connecting-IP;
```

**Option B: Authenticated Origin Pulls with your own certificate + firewall allowlist.** In the dashboard, enable zone-level (or per-hostname) Authenticated Origin Pulls with a client certificate **you** upload, install the matching CA at the origin (`ssl_client_certificate` + `ssl_verify_client on`, main document 3.4.3), and restrict ports 80/443 to Cloudflare ranges (main document 3.4.1). The shared global certificate only proves "the request came from Cloudflare", not "from your account".

### 11.3 Rule recipes (WAF custom rules and rate limits)

Expressions use Cloudflare's rule language. Names of fields/functions are stable but check the current reference when editing.

| # | Purpose | Expression | Action |
|---|---|---|---|
| 1 | Block secrets/VCS/test paths | `(http.request.uri.path contains "/.env") or (http.request.uri.path contains "/.git") or (http.request.uri.path contains "/vendor/phpunit")` | Block |
| 2 | Admin paths challenge outside trusted IPs | `starts_with(http.request.uri.path, "/admin") and not ip.src in {198.51.100.10 198.51.100.11}` | Managed Challenge |
| 3 | Restrict API methods | `starts_with(http.request.uri.path, "/api/") and not http.request.method in {"GET" "POST" "PUT" "PATCH" "DELETE" "OPTIONS"}` | Block |
| 4 | Login abuse (rate limit rule) | `http.request.uri.path eq "/login" and http.request.method eq "POST"` | Rate limit per IP (period/threshold per plan) then Managed Challenge or Block |
| 5 | Reset/OTP abuse (rate limit rule) | `http.request.uri.path in {"/forgot-password" "/two-factor-challenge"} and http.request.method eq "POST"` | Rate limit per IP |
| 6 | Regional noise reduction (optional) | `not ip.src.country in {"US" "CA" "GB"}` | Managed Challenge (never as authorisation) |

Profile guidance (which rules to spend limited rule counts on) is in the main document 3.3. Keep a documented break-glass step to disable a faulty rule quickly.

### 11.4 Verification commands

```bash
# 1. Origin must refuse direct access (replace with the real origin IP; run from outside the origin network)
curl -sk --max-time 10 --resolve example.com:443:<ORIGIN_IP> https://example.com/ -o /dev/null -w '%{http_code}\n'
#   SECURE: connection refused, TLS handshake failure, or 403/444. INSECURE: 200.

# 2. Through Cloudflare the site works and shows the edge
curl -sI https://example.com/ | grep -Ei '^(server|cf-ray|strict-transport-security)'

# 3. Forged client-IP header must not change what the app sees (check the app/Nginx log for the real IP)
curl -s https://example.com/ -H 'X-Forwarded-For: 203.0.113.99' -H 'CF-Connecting-IP: 203.0.113.99' -o /dev/null

# 4. WAF rule 1 fires
curl -s -o /dev/null -w '%{http_code}\n' https://example.com/.env      # expect 403 from Cloudflare (or 404 from origin)
```

### 11.5 Under Attack Mode runbook (temporary)

1. Confirm it is an HTTP flood (edge analytics); confirm the origin is locked (otherwise attackers bypass everything).
2. Add a targeted rule first (path/ASN/country/User-Agent pattern with Managed Challenge) where the pattern is clear.
3. Enable **Under Attack Mode** if the pattern is not clear; note that API clients and integrations will be challenged: notify partners and use a separate hostname for machine traffic in future.
4. Cache what can be cached; shed or disable the most expensive endpoints.
5. Watch origin CPU/DB, error rates and queue depth; scale if autoscaling exists.
6. Disable Under Attack Mode after traffic normalises; keep the targeted rules; write the incident review (main document Part 13).

---

## 12. Verification harness (tests and smoke script)

*Ref: Part 12.* Drop these into the project and run them in CI.

### 12.1 Pest tests: security baseline

```php
<?php
// tests/Feature/SecurityBaselineTest.php
use Illuminate\Support\Facades\Route;

it('sends baseline security headers on web responses', function () {
    $response = $this->get('/');
    $response->assertHeader('X-Content-Type-Options', 'nosniff');
    $response->assertHeader('Referrer-Policy');
    $csp = $response->headers->get('Content-Security-Policy') ?? $response->headers->get('Content-Security-Policy-Report-Only');
    expect($csp)->not->toBeNull();
    expect($csp)->toContain("frame-ancestors 'none'");
    expect($csp)->not->toContain("script-src 'unsafe-inline'");
});

it('requires authentication on every non-public route', function () {
    // Maintain this allowlist deliberately: every entry is a conscious "public" decision.
    $publicUris = [
        '/', 'login', 'register', 'forgot-password', 'reset-password/{token}', 'up',
        'sanctum/csrf-cookie', 'api/webhooks/provider',
    ];

    foreach (Route::getRoutes() as $route) {
        if (in_array($route->uri(), $publicUris, true) || $route->uri() === '_ignition/execute-solution') {
            continue;
        }
        $protected = collect($route->gatherMiddleware())->contains(
            fn ($m) => is_string($m) && (str_starts_with($m, 'auth') || str_starts_with($m, 'can:') || str_starts_with($m, 'signed'))
        );
        $this->assertTrue($protected, "Route [{$route->methods()[0]} {$route->uri()}] has no auth/can/signed middleware and is not in the public allowlist");
    }
});

it('does not run in debug mode in production-like testing', function () {
    config(['app.env' => 'production']);
    expect(config('app.debug'))->toBeFalse();
});

it('redacts sensitive keys in logs', function () {
    $processor = new \App\Logging\RedactSensitive();
    $record = new \Monolog\LogRecord(
        datetime: new \DateTimeImmutable(),
        channel: 'test',
        level: \Monolog\Level::Info,
        message: 'x',
        context: ['password' => 'hunter2', 'nested' => ['api_key' => 'abc', 'ok' => 'fine']],
    );
    $out = $processor($record);
    expect($out->context['password'])->toBe('[REDACTED]');
    expect($out->context['nested']['api_key'])->toBe('[REDACTED]');
    expect($out->context['nested']['ok'])->toBe('fine');
});
```

Authorisation, mass-assignment and rate-limit test templates are in the main document 12.4; the parallel-redemption race test is in H.4.

### 12.2 Post-deploy smoke script (staging and production, read-only)

```bash
#!/usr/bin/env bash
# security-smoke.sh https://example.com : read-only checks. Exit non-zero on any failure.
set -euo pipefail
BASE="${1:?usage: $0 https://example.com}"
fail=0

check_hidden() {   # path must NOT be served (anything but 200)
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${BASE}$1")
  if [ "$code" = "200" ]; then echo "FAIL  $1 returned 200"; fail=1; else echo "ok    $1 -> $code"; fi
}
for p in /.env /.git/config /storage/logs/laravel.log /vendor/composer/installed.json /composer.json \
         /artisan /phpinfo.php /info.php /telescope /horizon /_ignition/health-check /backup.sql /database.sql; do
  check_hidden "$p"
done

headers=$(curl -sI --max-time 10 "${BASE}/")
for h in x-content-type-options referrer-policy; do
  if echo "$headers" | grep -qi "^${h}:"; then echo "ok    header ${h}"; else echo "FAIL  missing header ${h}"; fail=1; fi
done
if echo "$headers" | grep -qiE '^(content-security-policy|content-security-policy-report-only):'; then
  echo "ok    CSP present"
else
  echo "FAIL  no CSP header"; fail=1
fi
if echo "$headers" | grep -qi '^x-powered-by:'; then echo "FAIL  X-Powered-By disclosed"; fail=1; fi

http_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${BASE/https:/http:}/")
case "$http_code" in 301|302|307|308) echo "ok    HTTP redirects ($http_code)";; *) echo "FAIL  HTTP not redirected ($http_code)"; fail=1;; esac

exit "$fail"
```

### 12.3 CI wiring (summary)

Run on every pull request: SAST (Semgrep), `composer audit --locked`, `npm audit --omit=dev`, secret scan, the Pest security tests, and the front-end CI guard from 8.1. Run nightly on staging: ZAP baseline scan and the smoke script. Run before each release: the authorisation matrix, the race test and the smoke script against the release candidate.

**Done when:** all of the above pass, legitimate user journeys still pass in the normal test suite, and any exception is recorded as an accepted risk with an owner and expiry.
