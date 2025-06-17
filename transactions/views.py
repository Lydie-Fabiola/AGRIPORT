from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Transaction
from .serializers import TransactionSerializer
from django.conf import settings
from .momo.client import MTNMomoClient
from .momo.collection import request_to_pay, get_payment_status
from .momo.disbursement import transfer, get_transfer_status
from reservations.models import Reservation
from django.utils import timezone
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(buyer=user)

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)

    @action(detail=False, methods=['post'], url_path='initiate-collection')
    def initiate_collection(self, request):
        phone = request.data.get('phone')
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'XAF')
        external_id = request.data.get('external_id', 'Farm2Market')
        payer_message = request.data.get('payer_message', '')
        payee_note = request.data.get('payee_note', '')
        client = MTNMomoClient(
            api_user=settings.MTN_MOMO_API_USER,
            api_key=settings.MTN_MOMO_API_KEY,
            subscription_key=settings.MTN_MOMO_COLLECTION_SUB_KEY,
            base_url=settings.MTN_MOMO_BASE_URL,
            target_env=settings.MTN_MOMO_TARGET_ENVIRONMENT,
        )
        reference_id = request_to_pay(client, phone, amount, currency, external_id, payer_message, payee_note)
        return Response({'reference_id': reference_id}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='collection-status')
    def collection_status(self, request):
        reference_id = request.query_params.get('reference_id')
        client = MTNMomoClient(
            api_user=settings.MTN_MOMO_API_USER,
            api_key=settings.MTN_MOMO_API_KEY,
            subscription_key=settings.MTN_MOMO_COLLECTION_SUB_KEY,
            base_url=settings.MTN_MOMO_BASE_URL,
            target_env=settings.MTN_MOMO_TARGET_ENVIRONMENT,
        )
        status_data = get_payment_status(client, reference_id)
        return Response(status_data)

    @action(detail=False, methods=['post'], url_path='initiate-disbursement')
    def initiate_disbursement(self, request):
        phone = request.data.get('phone')
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'XAF')
        external_id = request.data.get('external_id', 'Farm2Market')
        payer_message = request.data.get('payer_message', '')
        payee_note = request.data.get('payee_note', '')
        client = MTNMomoClient(
            api_user=settings.MTN_MOMO_API_USER,
            api_key=settings.MTN_MOMO_API_KEY,
            subscription_key=settings.MTN_MOMO_DISBURSE_SUB_KEY,
            base_url=settings.MTN_MOMO_BASE_URL,
            target_env=settings.MTN_MOMO_TARGET_ENVIRONMENT,
        )
        reference_id = transfer(client, phone, amount, currency, external_id, payer_message, payee_note)
        return Response({'reference_id': reference_id}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='disbursement-status')
    def disbursement_status(self, request):
        reference_id = request.query_params.get('reference_id')
        client = MTNMomoClient(
            api_user=settings.MTN_MOMO_API_USER,
            api_key=settings.MTN_MOMO_API_KEY,
            subscription_key=settings.MTN_MOMO_DISBURSE_SUB_KEY,
            base_url=settings.MTN_MOMO_BASE_URL,
            target_env=settings.MTN_MOMO_TARGET_ENVIRONMENT,
        )
        status_data = get_transfer_status(client, reference_id)
        return Response(status_data)

    @action(detail=False, methods=['post'], url_path='confirm')
    def confirm_transaction(self, request):
        reservation_id = request.data.get('reservation_id')
        phone = request.data.get('phone')  # Buyer's phone for MoMo
        try:
            reservation = Reservation.objects.get(id=reservation_id, buyer=request.user, status='approved')
        except Reservation.DoesNotExist:
            return Response({'detail': 'Reservation not found or not approved.'}, status=status.HTTP_400_BAD_REQUEST)
        # Initiate MoMo payment
        client = MTNMomoClient(
            api_user=settings.MTN_MOMO_API_USER,
            api_key=settings.MTN_MOMO_API_KEY,
            subscription_key=settings.MTN_MOMO_COLLECTION_SUB_KEY,
            base_url=settings.MTN_MOMO_BASE_URL,
            target_env=settings.MTN_MOMO_TARGET_ENVIRONMENT,
        )
        reference_id = request_to_pay(
            client,
            phone=phone,
            amount=reservation.quantity * reservation.product.price,
            currency='XAF',
            external_id=f'RES-{reservation.id}',
            payer_message='Farm2Market payment',
            payee_note='Thank you for your purchase!'
        )
        # Create transaction with pending status
        transaction = Transaction.objects.create(
            reservation=reservation,
            buyer=request.user,
            farmer=reservation.product.farmer,
            product=reservation.product,
            quantity=reservation.quantity,
            price=reservation.product.price,
            amount=reservation.quantity * reservation.product.price,
            currency='XAF',
            type='collection',
            status='pending',
            reference_id=reference_id
        )
        return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='check-payment')
    def check_payment(self, request, pk=None):
        transaction = self.get_object()
        client = MTNMomoClient(
            api_user=settings.MTN_MOMO_API_USER,
            api_key=settings.MTN_MOMO_API_KEY,
            subscription_key=settings.MTN_MOMO_COLLECTION_SUB_KEY,
            base_url=settings.MTN_MOMO_BASE_URL,
            target_env=settings.MTN_MOMO_TARGET_ENVIRONMENT,
        )
        status_data = get_payment_status(client, transaction.reference_id)
        # Update transaction status based on MoMo response
        momo_status = status_data.get('status')
        if momo_status == 'SUCCESSFUL':
            transaction.status = 'success'
        elif momo_status == 'FAILED':
            transaction.status = 'failed'
        elif momo_status == 'PENDING':
            transaction.status = 'pending'
        else:
            transaction.status = 'pending'
        transaction.momo_reference = status_data.get('financialTransactionId')
        transaction.save()
        return Response(TransactionSerializer(transaction).data)

class MoMoWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        # MoMo will POST payment status updates here
        data = request.data
        reference_id = data.get('externalId') or data.get('referenceId')
        status = data.get('status')
        momo_reference = data.get('financialTransactionId')
        from .models import Transaction
        try:
            txn = Transaction.objects.get(reference_id=reference_id)
        except Transaction.DoesNotExist:
            return Response({'detail': 'Transaction not found.'}, status=404)
        if status == 'SUCCESSFUL':
            txn.status = 'success'
        elif status == 'FAILED':
            txn.status = 'failed'
        elif status == 'PENDING':
            txn.status = 'pending'
        else:
            txn.status = 'pending'
        txn.momo_reference = momo_reference
        txn.save()
        return Response({'status': txn.status})
