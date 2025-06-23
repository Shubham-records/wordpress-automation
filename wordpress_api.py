
import requests
import json
import base64
import os
from typing import Dict, Any, Optional
import api_keys

class WordPressClient:
    """
    A utility class for interacting with WordPress API to upload images and create posts.
    """
    
    def __init__(self, site_url: str, username: str = None, app_password: str = None):
        """
        Initialize WordPress client.
        
        Args:
            site_url: The WordPress site URL (e.g., 'https://yoursite.com')
            username: WordPress username (optional if using app password from api_keys)
            app_password: WordPress application password (optional if in api_keys)
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        
        # Use provided credentials or fallback to api_keys
        if app_password:
            self.app_password = app_password
        else:
            self.app_password = api_keys.wordpress_api
            
        if username:
            self.username = username
        else:
            self.username = getattr(api_keys, 'WORDPRESS_USERNAME', 'admin')
        
        # Create authentication header
        credentials = f"{self.username}:{self.app_password}"
        token = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json'
        }
    
    def upload_image(self, image_path: str, title: str = None, alt_text: str = None) -> Dict[str, Any]:
        """
        Upload an image to WordPress media library.
        
        Args:
            image_path: Path to the image file
            title: Optional title for the image
            alt_text: Optional alt text for the image
            
        Returns:
            Dictionary containing upload result with media ID and URL
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Determine file extension and MIME type
        _, ext = os.path.splitext(image_path)
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_types.get(ext.lower(), 'image/jpeg')
        
        # Prepare file data
        filename = os.path.basename(image_path)
        if not title:
            title = os.path.splitext(filename)[0]
        
        # Read image file
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Prepare headers for file upload
        upload_headers = {
            'Authorization': self.headers['Authorization'],
            'Content-Type': mime_type,
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        
        try:
            # Upload to WordPress media library
            response = requests.post(
                f"{self.api_base}/media",
                headers=upload_headers,
                data=image_data
            )
            response.raise_for_status()
            
            media_data = response.json()
            media_id = media_data['id']
            
            # Update media with title and alt text if provided
            if title or alt_text:
                update_data = {}
                if title:
                    update_data['title'] = {'rendered': title}
                if alt_text:
                    update_data['alt_text'] = alt_text
                
                if update_data:
                    update_response = requests.post(
                        f"{self.api_base}/media/{media_id}",
                        headers=self.headers,
                        data=json.dumps(update_data)
                    )
                    if update_response.status_code == 200:
                        media_data = update_response.json()
            
            print(f"Successfully uploaded image: {media_data['source_url']}")
            return {
                'success': True,
                'media_id': media_id,
                'url': media_data['source_url'],
                'title': media_data.get('title', {}).get('rendered', ''),
                'alt_text': media_data.get('alt_text', ''),
                'data': media_data
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error uploading image to WordPress: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_post(self, title: str, content: str, status: str = 'draft', 
                   categories: list = None, tags: list = None, 
                   featured_media: int = None, excerpt: str = None) -> Dict[str, Any]:
        """
        Create a new WordPress post.
        
        Args:
            title: Post title
            content: Post content (HTML)
            status: Post status ('draft', 'publish', 'private', etc.)
            categories: List of category names or IDs
            tags: List of tag names
            featured_media: Media ID for featured image
            excerpt: Post excerpt
            
        Returns:
            Dictionary containing post creation result
        """
        post_data = {
            'title': title,
            'content': content,
            'status': status
        }
        
        if excerpt:
            post_data['excerpt'] = excerpt
        
        if featured_media:
            post_data['featured_media'] = featured_media
        
        # Handle categories
        if categories:
            category_ids = []
            for cat in categories:
                if isinstance(cat, int):
                    category_ids.append(cat)
                else:
                    # Try to find category by name or create it
                    cat_id = self.get_or_create_category(cat)
                    if cat_id:
                        category_ids.append(cat_id)
            
            if category_ids:
                post_data['categories'] = category_ids
        
        # Handle tags
        if tags:
            tag_ids = []
            for tag in tags:
                if isinstance(tag, int):
                    tag_ids.append(tag)
                else:
                    # Try to find tag by name or create it
                    tag_id = self.get_or_create_tag(tag)
                    if tag_id:
                        tag_ids.append(tag_id)
            
            if tag_ids:
                post_data['tags'] = tag_ids
        
        try:
            response = requests.post(
                f"{self.api_base}/posts",
                headers=self.headers,
                data=json.dumps(post_data)
            )
            response.raise_for_status()
            
            post_result = response.json()
            print(f"Successfully created WordPress post: {post_result['link']}")
            
            return {
                'success': True,
                'post_id': post_result['id'],
                'url': post_result['link'],
                'edit_url': f"{self.site_url}/wp-admin/post.php?post={post_result['id']}&action=edit",
                'status': post_result['status'],
                'data': post_result
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error creating WordPress post: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_or_create_category(self, category_name: str) -> Optional[int]:
        """
        Get category ID by name or create if it doesn't exist.
        
        Args:
            category_name: Name of the category
            
        Returns:
            Category ID or None if failed
        """
        try:
            # Search for existing category
            response = requests.get(
                f"{self.api_base}/categories",
                headers=self.headers,
                params={'search': category_name}
            )
            response.raise_for_status()
            
            categories = response.json()
            for cat in categories:
                if cat['name'].lower() == category_name.lower():
                    return cat['id']
            
            # Create new category if not found
            create_response = requests.post(
                f"{self.api_base}/categories",
                headers=self.headers,
                data=json.dumps({'name': category_name})
            )
            
            if create_response.status_code == 201:
                return create_response.json()['id']
            
        except requests.exceptions.RequestException as e:
            print(f"Error handling category '{category_name}': {e}")
        
        return None
    
    def get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """
        Get tag ID by name or create if it doesn't exist.
        
        Args:
            tag_name: Name of the tag
            
        Returns:
            Tag ID or None if failed
        """
        try:
            # Search for existing tag
            response = requests.get(
                f"{self.api_base}/tags",
                headers=self.headers,
                params={'search': tag_name}
            )
            response.raise_for_status()
            
            tags = response.json()
            for tag in tags:
                if tag['name'].lower() == tag_name.lower():
                    return tag['id']
            
            # Create new tag if not found
            create_response = requests.post(
                f"{self.api_base}/tags",
                headers=self.headers,
                data=json.dumps({'name': tag_name})
            )
            
            if create_response.status_code == 201:
                return create_response.json()['id']
            
        except requests.exceptions.RequestException as e:
            print(f"Error handling tag '{tag_name}': {e}")
        
        return None
    
    def update_post(self, post_id: int, **kwargs) -> Dict[str, Any]:
        """
        Update an existing WordPress post.
        
        Args:
            post_id: ID of the post to update
            **kwargs: Fields to update (title, content, status, etc.)
            
        Returns:
            Dictionary containing update result
        """
        try:
            response = requests.post(
                f"{self.api_base}/posts/{post_id}",
                headers=self.headers,
                data=json.dumps(kwargs)
            )
            response.raise_for_status()
            
            return {'success': True, 'data': response.json()}
            
        except requests.exceptions.RequestException as e:
            print(f"Error updating WordPress post: {e}")
            return {'success': False, 'error': str(e)}


# Example usage
def example_usage():
    # Initialize WordPress client
    wp_client = WordPressClient('https://yoursite.com', 'username', 'app_password')
    
    # Upload an image
    image_result = wp_client.upload_image(
        'path/to/image.jpg',
        title='My Image Title',
        alt_text='Description of the image'
    )
    
    if image_result['success']:
        # Create a post with the uploaded image
        post_result = wp_client.create_post(
            title='My Blog Post',
            content=f'<img src="{image_result["url"]}" alt="{image_result["alt_text"]}"><p>Post content here...</p>',
            status='draft',
            categories=['Finance', 'Business'],
            tags=['investing', 'money'],
            featured_media=image_result['media_id']
        )
        
        if post_result['success']:
            print(f"Post created: {post_result['url']}")
        else:
            print(f"Failed to create post: {post_result['error']}")
    else:
        print(f"Failed to upload image: {image_result['error']}")


if __name__ == "__main__":
    # Uncomment to run the example
    # example_usage()
    pass
