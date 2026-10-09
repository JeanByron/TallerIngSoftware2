<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\BulkStoreUsersRequest;
use App\Models\User;
use Carbon\Carbon;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;

class UserController extends Controller
{
    public const DEFAULT_PER_PAGE = 50;

    public const MAX_PER_PAGE = 200;

    public function index(Request $request): JsonResponse
    {
        return response()->json($this->paginate($request, User::query()));
    }

    public function emails(Request $request): JsonResponse
    {
        return response()->json($this->paginate($request, User::query(), ['id', 'email']));
    }

    public function overTwenty(Request $request): JsonResponse
    {
        $cutoff = Carbon::now()->subYears(20)->startOfDay();

        // El filtro se hace en SQL (usa el índice de birth_date) en lugar de cargar toda la tabla en PHP.
        $query = User::query()->where('birth_date', '<=', $cutoff->toDateString());

        return response()->json(
            ['cutoff_date' => $cutoff->toDateString()] + $this->paginate($request, $query)
        );
    }

    public function bulkStore(BulkStoreUsersRequest $request): JsonResponse
    {
        $created = [];

        foreach ($request->validated()['users'] as $userData) {
            $created[] = User::create([
                'name' => $userData['name'],
                'email' => $userData['email'],
                'birth_date' => $userData['birth_date'],
                'password' => Hash::make($userData['password'] ?? 'password'),
            ]);
        }

        return response()->json([
            'message' => 'Se crearon 3 usuarios correctamente.',
            'users' => $created,
        ], 201);
    }

    /**
     * Pagina la consulta según ?page= y ?per_page= (máximo MAX_PER_PAGE).
     */
    private function paginate(Request $request, Builder $query, array $columns = ['*']): array
    {
        $validated = $request->validate([
            'page' => ['sometimes', 'integer', 'min:1'],
            'per_page' => ['sometimes', 'integer', 'min:1', 'max:'.self::MAX_PER_PAGE],
        ]);

        $page = (int) ($validated['page'] ?? 1);
        $perPage = (int) ($validated['per_page'] ?? self::DEFAULT_PER_PAGE);

        $paginator = $query->orderBy('id')->paginate($perPage, $columns, 'page', $page);

        return [
            'total' => $paginator->total(),
            'page' => $paginator->currentPage(),
            'per_page' => $paginator->perPage(),
            'last_page' => $paginator->lastPage(),
            'data' => $paginator->items(),
        ];
    }
}
