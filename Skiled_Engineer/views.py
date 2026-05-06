from django.shortcuts import redirect


def root_views(request):
    return redirect('api-root')