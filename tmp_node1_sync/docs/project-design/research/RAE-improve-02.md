Co nadal jest słabe / ryzykowne w kodzie (nie w docsach)
3.1. Auth: stare i nowe podejście jednocześnie

Masz dwa światy:

W apps/memory_api/security/auth.py:

security = HTTPBearer(...),

verify_api_key(...) – respektuje ENABLE_API_KEY_AUTH,

verify_token(...) – łączy JWT + API key,

get_current_user(), check_tenant_access().

W apps/memory_api/dependencies.py:

własne get_api_key() z APIKeyHeader,

które ignoruje ENABLE_API_KEY_AUTH i patrzy tylko na settings.API_KEY.

A potem:

w main.py globalnie dodajesz Depends(auth.verify_token) – super,

ale w api/v1/memory.py router ma jeszcze dependencies=[Depends(get_api_key)].

Czyli:

część kodu używa nowego modułu security/auth.py,

część – starego, prostego helpera.

Efekt uboczny:
jeżeli w ENV masz ustawione API_KEY (domyślnie w config.py jest "secret"), to get_api_key będzie wymagał klucza nawet wtedy, gdy ENABLE_API_KEY_AUTH=False.
Czyli logiczna ścieżka:

flagi mówią „auth wyłączony”, ale handler nadal wymaga klucza.

To jest typowy „refactor w połowie” – w kodzie to widać.

3.2. Tenancy: ID jest używane, ale brak realnego sprawdzenia „czy wolno”

Kod robi:

w TenantContextMiddleware – bierze X-Tenant-Id z nagłówka albo z query param i przepycha do request.state.tenant_id,

w repozytoriach/serwisach – tenant_id jest parametrem i trafia do SQL / Qdrant.

Ale:

funkcja check_tenant_access w security/auth.py istnieje, ale jej nie widzę podpiętej jako dependency nigdzie przy endpointach.

Czyli z punktu widzenia kodu:

jak tylko przejdziesz verify_token() (czyli masz ważny JWT / API key),

możesz użyć dowolnego X-Tenant-Id.

To nie jest bug na poziomie „zapomniałem headeru”, tylko raczej brak realnego RBAC/ABAC:
system wie, że są tenanty, używa ich w danych, ale nie sprawdza, czy dany użytkownik może dotykać tego konkretnego tenant_id.

3.3. Memory decay – jest serwis, nie ma scheduler’a

W usługach:

ImportanceScoringService ma metodę decay_importance(...),

logika decay jest dosyć zaawansowana (różne tempo dla „świeżych”, normalnych i starych wspomnień),

widzę przykłady wywołań typu:

# Daily cron job
await scoring_service.decay_importance(...)


Ale:

te wywołania, które znalazłem, są w komentarzach / przykładach,

nie trafiłem na realny kod:

ani w Celery taskach,

ani w jakimś cron.py,

ani w pipeline’ach, który faktycznie to odpala.

Czyli z perspektywy kodu:
model i algorytm decay istnieją, ale są „zawieszone w próżni” – nie ma scheduler’a, który je uruchamia.

3.4. Governance endpointy bez twardych zależności auth

apps/memory_api/api/v1/governance.py:

router ma tylko:

router = APIRouter(prefix="/v1/governance", tags=["Governance"])


importuje get_db_pool, ale nie widzę tam Depends(auth.verify_token) ani Depends(get_api_key).

W praktyce pewną ochronę daje globalny dependencies=(Depends(auth.verify_token)... w FastAPI(...) – ale tylko wtedy, gdy włączysz flagi ENABLE_API_KEY_AUTH / ENABLE_JWT_AUTH.

Jeżeli ktoś odpali RAE w trybie:

ENABLE_API_KEY_AUTH = False

ENABLE_JWT_AUTH = False

to governance będzie kompletnie otwarte (tenant_id idzie parametrem ścieżki, więc można bawić się w „enumerowanie tenantów” – oczywiście przy braku innych ochron).

3.5. Kilka miejsc „w połowie refaktoru”

Po samym kodzie widać jeszcze:

Stare helpery typu get_api_key obok nowego auth w security/.

Comments w stylu:

# Tu w realu: SET LOCAL app.current_tenant_id = :tenant_id


a realny SET LOCAL jest robiony w repozytorium, ale middleware tylko dopisuje do request.state.

Funkcje w security/auth.py (check_tenant_access, może jakieś user-info) które nie są nigdzie użyte jako dependencies.