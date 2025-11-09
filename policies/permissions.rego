package permissions

import future.keywords.if
import future.keywords.in

default allow = false

# Get all matching roles for a user and application across all environments and AD groups
# This is a helper set that collects all possible role matches
user_roles[app_id] contains role if {
    some app_id
    some env
    some group in input.user.ad_groups
    role := data.role_mappings[app_id][env][group]
}

# Get user's role for a specific application
# Returns the highest priority role (admin > user) if user has multiple roles
user_role[app_id] := "admin" if {
    some app_id
    "admin" in user_roles[app_id]
}

user_role[app_id] := "user" if {
    some app_id
    "user" in user_roles[app_id]
    not "admin" in user_roles[app_id]
}

# Evaluate permissions for all applications
# Returns the role for each application where a match is found, or "none" if no match
permissions[app_id] := role if {
    some app_id in input.applications
    role := user_role[app_id]
}

permissions[app_id] := "none" if {
    some app_id in input.applications
    not user_role[app_id]
}
