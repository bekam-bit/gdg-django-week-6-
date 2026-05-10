from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import TemplateHTMLRenderer,JSONRenderer
from .serrializer import AuthorSerializer
from rest_framework.response import Response
from rest_framework import status
from .models import Author
from rest_framework.exceptions import NotFound

@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def author_list(request):
    # Content negotiation: HTML for pages, JSON for API clients.
    authors=Author.objects.all()
    serializer=AuthorSerializer(authors,many=True)
    
    if request.accepted_renderer.format=="json":
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    return Response({'authors':authors},template_name='lmsApp/author pages/author_list.html')

@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer,JSONRenderer])
def author_details(request,author_id):
    # Keep API and template responses in sync for the same endpoint.
    try:
        author=Author.objects.get(pk=author_id)
    except Author.DoesNotExist:
        raise NotFound("Author Not Found")
    
    serializer=AuthorSerializer(author)

    if request.accepted_renderer.format=="json":
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    return Response({'author':author},template_name='lmsApp/author pages/author_details.html')