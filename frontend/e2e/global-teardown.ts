
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import path from 'path';

async function globalTeardown() {
    console.log('Global Teardown: Starting cleanup...');

    // Load environment variables from the root .env file
    // Assuming frontend/ is the current working directory, root is ../.env
    const envPath = path.resolve(__dirname, '../../.env');
    console.log(`Loading .env from ${envPath}`);
    dotenv.config({ path: envPath });

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!supabaseUrl || !supabaseServiceKey) {
        console.warn('Global Teardown: Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY. Skipping cleanup.');
        return;
    }

    const supabase = createClient(supabaseUrl, supabaseServiceKey, {
        auth: {
            autoRefreshToken: false,
            persistSession: false,
        },
    });

    const { data: { users }, error } = await supabase.auth.admin.listUsers();

    if (error) {
        console.error('Global Teardown: Failed to list users:', error);
        return;
    }

    console.log(`Global Teardown: Found ${users.length} total users.`);

    const testUsers = users.filter((user) => user.email?.startsWith('e2e-test-'));

    if (testUsers.length === 0) {
        console.log('Global Teardown: No test users found to clean up.');
        return;
    }

    console.log(`Global Teardown: Found ${testUsers.length} test users to delete.`);

    for (const user of testUsers) {
        const { error: deleteError } = await supabase.auth.admin.deleteUser(user.id);
        if (deleteError) {
            console.error(`Global Teardown: Failed to delete user ${user.email} (${user.id}):`, deleteError);
        } else {
            console.log(`Global Teardown: Deleted user ${user.email}`);
        }
    }

    console.log('Global Teardown: Cleanup complete.');
}

export default globalTeardown;
