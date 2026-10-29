@require_POST
def cliente_registro_api(request):
    data = json.loads(request.body)
    nombre = data.get('nombre', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not nombre or not email or not password:
        return JsonResponse({'status': 'error', 'message': 'Todos los campos son obligatorios.'}, status=400)

    if User.objects.filter(username=email).exists() or Cliente.objects.filter(email=email).exists():
        return JsonResponse({'status': 'error', 'message': 'El correo ya se encuentra registrado.'}, status=400)

    with transaction.atomic():
        user = User.objects.create_user(username=email, email=email, password=password, first_name=nombre)
        grupo_cliente, _ = Group.objects.get_or_create(name='cliente')
        user.groups.add(grupo_cliente)
        Cliente.objects.create(user=user, nombre_completo=nombre, email=email)

    return JsonResponse({'status': 'ok', 'message': 'Cuenta creada con éxito. Ahora puedes iniciar sesión.'})

@require_POST
def cliente_login_api(request):
    data = json.loads(request.body)
    email = data.get('email', '').strip()
    password = data.get('password', '')

    user = authenticate(request, username=email, password=password)
    if user is not None:
        login(request, user)
        cliente = Cliente.objects.filter(email=email).first()
        nombre = cliente.nombre_completo if cliente else user.first_name or user.username
        return JsonResponse({'status': 'ok', 'nombre': nombre, 'email': email})
    else:
        return JsonResponse({'status': 'error', 'message': 'Correo o contraseña incorrectos.'}, status=400)

@require_POST
def cliente_logout_api(request):
    logout(request)
    return JsonResponse({'status': 'ok', 'message': 'Sesión cerrada.'})
