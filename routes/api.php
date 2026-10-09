<?php

use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Here is where you can register API routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| is assigned the "api" middleware group. Enjoy building your API!
|
*/

use App\Http\Controllers\Api\UserController;

Route::get('/users', [UserController::class, 'index']);
Route::get('/users/emails', [UserController::class, 'emails']);
Route::get('/users/over-twenty', [UserController::class, 'overTwenty']);
Route::post('/users/bulk', [UserController::class, 'bulkStore']);
