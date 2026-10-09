<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class BulkStoreUsersRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'users' => ['required', 'array', 'size:3'],
            'users.*.name' => ['required', 'string', 'max:255'],
            'users.*.email' => ['required', 'email', 'max:255', 'distinct', 'unique:users,email'],
            'users.*.birth_date' => ['required', 'date', 'before_or_equal:today'],
            'users.*.password' => ['nullable', 'string', 'min:6'],
        ];
    }

    public function messages(): array
    {
        return [
            'users.size' => 'Debe enviar exactamente 3 usuarios en el arreglo "users".',
            'users.*.email.distinct' => 'Los correos de los 3 usuarios deben ser diferentes entre sí.',
        ];
    }
}
