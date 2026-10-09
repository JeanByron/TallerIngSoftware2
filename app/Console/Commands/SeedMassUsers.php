<?php

namespace App\Console\Commands;

use Database\Seeders\MassUserSeeder;
use Illuminate\Console\Command;

class SeedMassUsers extends Command
{
    protected $signature = 'users:seed-mass
                            {--count=1500000 : Cantidad total de usuarios}
                            {--chunk=2000 : Tamaño de lote por inserción}';

    protected $description = 'Pobla la tabla users con datos masivos para pruebas de carga (Locust)';

    public function handle(): int
    {
        $_ENV['MASS_USER_SEED_COUNT'] = (string) $this->option('count');
        $_ENV['MASS_USER_CHUNK_SIZE'] = (string) $this->option('chunk');

        $seeder = $this->laravel->make(MassUserSeeder::class);
        $seeder->setCommand($this);
        $seeder->run();

        return self::SUCCESS;
    }
}
